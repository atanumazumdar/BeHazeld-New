"""
SalesService — atomic sales transaction engine.

create_sale() executes one database transaction:

  Phase 1 — VALIDATE (read-only, no writes)
  ──────────────────────────────────────────
  1a. Validate customer exists (if customer_id supplied)
  1b. Validate every product variant exists
  1c. Availability Guard: check quantity_available for EVERY line at the
      specified (location_id, bin_id) before writing a single byte.
      → Raises StockNotAvailableError immediately on the first shortfall.

  Phase 2 — GENERATE (CPU-only, no I/O)
  ──────────────────────────────────────
  2a. Compute per-line totals and bill-level aggregates
  2b. Generate invoice_number (count-based sequence)
  2c. Generate PDF bytes in memory (ReportLab — no file write yet)
      → If PDF generation raises, the exception propagates, rollback fires,
        and no stock has been touched.

  Phase 3 — WRITE (all inside the open transaction)
  ──────────────────────────────────────────────────
  3a. Create SaleBill header
  3b. For each line:
        - Create SaleBillLine
        - append_ledger_entry (SALE_OUT, negative quantity_change)
        - upsert_balance (negative delta)
  3c. Create SalePayment
  3d. db.commit()  ← single commit point

  Phase 4 — FILE I/O (after commit — can be retried without data loss)
  ────────────────────────────────────────────────────────────────────
  4a. Save PDF bytes to INVOICE_STORAGE_PATH/{tenant_id}/{invoice_number}.pdf

Why InventoryRepository directly (not InventoryService)?
---------------------------------------------------------
InventoryService.record_stock_movement() commits internally. Calling it N
times would produce N separate commits, making full rollback impossible.
Using InventoryRepository methods directly (same Session) keeps everything
inside one atomic transaction.

Atomicity guarantees
--------------------
* Partial Stock Failure — if ANY line is short, Phase 1 aborts before Phase 3.
  No stock is deducted; no bill is created.
* PDF Failure — if Phase 2c raises (corrupt font cache, memory error, etc.),
  the except block calls db.rollback(). Phase 3 never started, so no stock
  is deducted and no bill is created.
* Payment Failure — if Phase 3c raises, rollback fires, stock reverts.
"""
import csv
import io
import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, StockNotAvailableError, ValidationError
from app.db.base import Base
from app.models.catalog import Color, Product, ProductVariant, Size
from app.models.inventory import Bin, MovementType
from app.models.sales import Customer, SaleBill, SaleBillLine, SalePayment
from app.models.tenant import Location
from app.repositories.catalog_repository import CatalogRepository
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.sales_repository import SalesRepository, generate_invoice_number
from app.schemas.sales import (
    CreateCustomerRequest,
    CreateSaleBillRequest,
    CreateSaleBillLineRequest,
    CreateSalePaymentRequest,
    InvoiceMetadata,
    SaleBillResponse,
    SalesInvoiceImportResponse,
)
from app.services.inventory_service import InventoryService
from app.services import report_service


class SalesService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = SalesRepository(db)
        self.inv_repo = InventoryRepository(db)
        self.catalog_repo = CatalogRepository(db)
        self._finance_svc = None   # injected lazily; None → skip journal posting

    def ensure_sales_tables_available(self) -> None:
        """Create sales schema tables on first-run production databases."""
        bind = self.db.get_bind()
        dialect_name = getattr(getattr(bind, "dialect", None), "name", None)
        if dialect_name != "postgresql":
            return

        with bind.begin() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS sales"))

        Base.metadata.create_all(
            bind=bind,
            tables=[
                Customer.__table__,
                SaleBill.__table__,
                SaleBillLine.__table__,
                SalePayment.__table__,
            ],
        )

    # ── Customer management ───────────────────────────────────────────────────

    def create_customer(
        self, tenant_id: uuid.UUID, req: CreateCustomerRequest
    ) -> Customer:
        self.ensure_sales_tables_available()
        try:
            c = self.repo.create_customer(
                tenant_id=tenant_id,
                name=req.name,
                email=req.email,
                phone=req.phone,
                address=req.address,
            )
            self.db.commit()
            self.db.refresh(c)
            return c
        except Exception:
            self.db.rollback()
            raise

    def list_customers(
        self, tenant_id: uuid.UUID, search: Optional[str] = None
    ) -> list[Customer]:
        self.ensure_sales_tables_available()
        return self.repo.list_customers(tenant_id, search=search)

    def get_customer(self, tenant_id: uuid.UUID, customer_id: uuid.UUID) -> Customer:
        self.ensure_sales_tables_available()
        return self.repo.get_customer_by_id(tenant_id, customer_id)

    # ── The main sales transaction ────────────────────────────────────────────

    def create_sale(
        self,
        tenant_id: uuid.UUID,
        req: CreateSaleBillRequest,
        tenant_name: str = "BeHazeld",
        performed_by_user_id: uuid.UUID | None = None,
        invoice_number_override: str | None = None,
        generate_pdf: bool = True,
    ) -> tuple[SaleBill, InvoiceMetadata]:
        """
        Execute the atomic sale transaction.

        Returns
        -------
        (SaleBill, InvoiceMetadata) — the persisted bill and PDF metadata.

        Raises
        ------
        NotFoundError           — customer or any variant not found
        StockNotAvailableError  — any line item has insufficient stock
        ConflictError           — duplicate invoice number (shouldn't happen;
                                  sequence is tenant-monotonic)
        """
        self.ensure_sales_tables_available()
        try:
            # ── Phase 1a: validate customer ───────────────────────────────────
            if req.customer_id is not None:
                self.repo.get_customer_by_id(tenant_id, req.customer_id)

            # ── Phase 1b: validate all variants ──────────────────────────────
            variants = []
            for line_req in req.lines:
                variant = self.catalog_repo.get_variant_by_id(
                    tenant_id, line_req.product_variant_id
                )
                variants.append(variant)

            # ── Phase 1c: AVAILABILITY GUARD (check ALL before writing ANY) ──
            for line_req in req.lines:
                balance = self.inv_repo.get_balance(
                    tenant_id,
                    line_req.product_variant_id,
                    req.location_id,
                    req.bin_id,
                )
                available = balance.quantity_available if balance is not None else Decimal("0")
                if available < line_req.quantity:
                    raise StockNotAvailableError(
                        f"Only {available} units available for variant "
                        f"{line_req.product_variant_id}; requested {line_req.quantity}"
                    )

            # ── Phase 2a: compute totals ──────────────────────────────────────
            line_totals: list[Decimal] = []
            total_amount = Decimal("0")
            tax_amount = Decimal("0")
            total_discount = Decimal("0")

            for line_req in req.lines:
                net_price   = line_req.selling_price - line_req.discount_amount
                line_total  = (line_req.quantity * net_price * (
                    1 + line_req.tax_rate
                )).quantize(Decimal("0.01"))
                line_tax    = (line_req.quantity * net_price * line_req.tax_rate
                               ).quantize(Decimal("0.01"))
                line_disc   = (line_req.quantity * line_req.discount_amount
                               ).quantize(Decimal("0.01"))

                line_totals.append(line_total)
                total_amount   += line_total
                tax_amount     += line_tax
                total_discount += line_disc

            # ── Phase 2b: generate invoice number ─────────────────────────────
            if invoice_number_override:
                invoice_number = invoice_number_override.strip()
                if self.repo.get_bill_by_invoice_number(tenant_id, invoice_number) is not None:
                    raise ValidationError(f"Invoice '{invoice_number}' already exists")
            else:
                seq = self.repo.count_bills_by_tenant(tenant_id) + 1
                invoice_number = generate_invoice_number(seq)

            # ── Phase 2c: generate PDF bytes (CPU-only) ───────────────────────
            # Build a lightweight bill proxy for the PDF renderer — we don't
            # have a persisted ORM object yet, so we pass data as attributes.
            bill_proxy = _BillProxy(
                invoice_number=invoice_number,
                bill_date=req.bill_date,
                customer_name=(
                    self.repo.get_customer_by_id(tenant_id, req.customer_id).name
                    if req.customer_id else None
                ),
                lines_data=[(lr, lt) for lr, lt in zip(req.lines, line_totals)],
                total_amount=total_amount,
                tax_amount=tax_amount,
                total_discount=total_discount,
                payment=req.payment,
            )
            pdf_bytes = (
                report_service.generate_invoice_pdf(bill_proxy, tenant_name)
                if generate_pdf
                else b""
            )

            # ── Phase 3a: create bill header ──────────────────────────────────
            bill = self.repo.create_bill(
                tenant_id=tenant_id,
                invoice_number=invoice_number,
                bill_date=req.bill_date,
                location_id=req.location_id,
                bin_id=req.bin_id,
                total_amount=total_amount,
                tax_amount=tax_amount,
                total_discount=total_discount,
                customer_id=req.customer_id,
                notes=req.notes,
            )

            # ── Phase 3b: lines + stock deduction ────────────────────────────
            for line_req, line_total in zip(req.lines, line_totals):
                self.repo.create_bill_line(
                    tenant_id=tenant_id,
                    bill_id=bill.id,
                    product_variant_id=line_req.product_variant_id,
                    quantity=line_req.quantity,
                    selling_price=line_req.selling_price,
                    unit_cost=Decimal("0"),   # Phase 5: populate from batch FIFO
                    tax_rate=line_req.tax_rate,
                    discount_amount=line_req.discount_amount,
                    total_line_amount=line_total,
                )
                # Deduct stock — SALE_OUT is negative quantity_change
                self.inv_repo.append_ledger_entry(
                    tenant_id=tenant_id,
                    product_variant_id=line_req.product_variant_id,
                    location_id=req.location_id,
                    bin_id=req.bin_id,
                    movement_type=MovementType.SALE_OUT,
                    quantity_change=-line_req.quantity,   # negative: outward
                    unit_cost=line_req.selling_price,
                    reference_type="sale_bill",
                    reference_id=bill.id,
                    notes=f"Sale invoice {invoice_number}",
                    performed_by_user_id=performed_by_user_id,
                )
                self.inv_repo.upsert_balance(
                    tenant_id=tenant_id,
                    product_variant_id=line_req.product_variant_id,
                    location_id=req.location_id,
                    bin_id=req.bin_id,
                    quantity_delta=-line_req.quantity,  # negative: reduce balance
                )

            # ── Phase 3c: record payment ──────────────────────────────────────
            self.repo.create_payment(
                tenant_id=tenant_id,
                bill_id=bill.id,
                payment_date=req.bill_date,
                amount=req.payment.amount,
                payment_mode=str(req.payment.payment_mode),
                transaction_id=req.payment.transaction_id,
                notes=req.payment.notes,
            )

            # ── Phase 3e: post accounting journal (same transaction) ──────────
            if self._finance_svc is not None:
                self._finance_svc.post_sale_journal(
                    tenant_id=tenant_id,
                    ref_id=bill.id,
                    entry_date=req.bill_date,
                    total_amount=total_amount,
                )

            # ── Phase 3d: single commit ───────────────────────────────────────
            self.db.commit()
            self.db.refresh(bill)

        except Exception:
            self.db.rollback()
            raise

        # ── Phase 4: save PDF to disk (post-commit; safe to retry) ───────────
        metadata = (
            report_service.save_invoice_pdf(pdf_bytes, tenant_id, invoice_number)
            if generate_pdf
            else InvoiceMetadata(invoice_number=invoice_number, file_path="", file_size_bytes=0)
        )
        return bill, metadata

    # ── Sales CSV import ─────────────────────────────────────────────────────

    def import_invoice_csv(
        self,
        tenant_id: uuid.UUID,
        csv_bytes: bytes,
        performed_by_user_id: uuid.UUID | None = None,
    ) -> SalesInvoiceImportResponse:
        """
        Import sale invoices from CSV.

        Required columns:
        invoice_number,bill_date,customer_name,sku_code,quantity,selling_price

        Optional columns:
        product_name,resolved_sku_code,payment_mode,tax_rate,discount_amount,notes,transaction_id
        """
        self.ensure_sales_tables_available()
        InventoryService(self.db).ensure_inventory_tables_available()
        location, bin_obj = self._default_sale_location_bin(tenant_id)

        try:
            text = csv_bytes.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValidationError("CSV must be UTF-8 encoded") from exc

        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            raise ValidationError("CSV file is empty")

        normalised_headers = {self._norm_header(h): h for h in reader.fieldnames}
        required = {"invoice_number", "bill_date", "customer_name", "sku_code", "quantity", "selling_price"}
        missing = sorted(required - set(normalised_headers))
        if missing:
            raise ValidationError(f"Missing required CSV columns: {', '.join(missing)}")

        grouped: dict[str, list[dict[str, str]]] = {}
        row_numbers: dict[str, list[int]] = {}
        for index, raw_row in enumerate(reader, start=2):
            row = {self._norm_header(k): (v or "").strip() for k, v in raw_row.items() if k is not None}
            invoice_number = row.get("invoice_number", "")
            if not invoice_number:
                grouped.setdefault("", []).append(row)
                row_numbers.setdefault("", []).append(index)
                continue
            grouped.setdefault(invoice_number, []).append(row)
            row_numbers.setdefault(invoice_number, []).append(index)

        imported = 0
        skipped = 0
        errors: list[str] = []
        invoices: list[str] = []

        for invoice_number, rows in grouped.items():
            label = invoice_number or f"row {row_numbers.get(invoice_number, ['?'])[0]}"
            if not invoice_number:
                skipped += 1
                errors.append(f"{label}: invoice_number is required")
                continue
            if self.repo.get_bill_by_invoice_number(tenant_id, invoice_number) is not None:
                skipped += 1
                invoices.append(invoice_number)
                continue

            try:
                bill_date = self._parse_date(rows[0].get("bill_date", ""))
                customer_id = self._customer_id_for_import(tenant_id, rows[0].get("customer_name", ""))
                lines: list[CreateSaleBillLineRequest] = []
                total_amount = Decimal("0")

                for row in rows:
                    sku_code = row.get("sku_code", "")
                    resolved_sku_code = row.get("resolved_sku_code", "")
                    lookup_sku = resolved_sku_code or sku_code
                    variant = self._resolve_import_variant(
                        tenant_id,
                        lookup_sku,
                        product_name=row.get("product_name", ""),
                    )
                    if variant is None:
                        raise ValidationError(f"SKU '{lookup_sku}' not found")

                    quantity = self._parse_decimal(row.get("quantity", ""), "quantity")
                    selling_price = self._parse_decimal(row.get("selling_price", ""), "selling_price")
                    tax_rate = self._parse_decimal(row.get("tax_rate", "0"), "tax_rate")
                    discount_amount = self._parse_decimal(row.get("discount_amount", "0"), "discount_amount")
                    net_price = selling_price - discount_amount
                    line_total = (quantity * net_price * (Decimal("1") + tax_rate)).quantize(Decimal("0.01"))
                    total_amount += line_total

                    lines.append(
                        CreateSaleBillLineRequest(
                            product_variant_id=variant.id,
                            quantity=quantity,
                            selling_price=selling_price,
                            tax_rate=tax_rate,
                            discount_amount=discount_amount,
                        )
                    )

                first_row = rows[0]
                payment_mode = first_row.get("payment_mode", "cash") or "cash"
                req = CreateSaleBillRequest(
                    location_id=location.id,
                    bin_id=bin_obj.id,
                    bill_date=bill_date,
                    customer_id=customer_id,
                    notes=first_row.get("notes") or f"Imported sales invoice {invoice_number}",
                    lines=lines,
                    payment=CreateSalePaymentRequest(
                        amount=total_amount,
                        payment_mode=payment_mode,
                        transaction_id=first_row.get("transaction_id") or None,
                        notes=f"Imported payment for invoice {invoice_number}",
                    ),
                )
                self.create_sale(
                    tenant_id=tenant_id,
                    req=req,
                    performed_by_user_id=performed_by_user_id,
                    invoice_number_override=invoice_number,
                    generate_pdf=False,
                )
                imported += 1
                invoices.append(invoice_number)
            except Exception as exc:
                skipped += 1
                self.db.rollback()
                errors.append(f"{label}: {getattr(exc, 'message', str(exc))}")

        return SalesInvoiceImportResponse(
            imported=imported,
            skipped=skipped,
            errors=errors,
            invoices=invoices,
        )

    def _default_sale_location_bin(self, tenant_id: uuid.UUID) -> tuple[Location, Bin]:
        location = self.db.scalar(
            select(Location)
            .where(Location.tenant_id == tenant_id, Location.is_active.is_(True))
            .order_by(Location.name)
        )
        if location is None:
            raise ValidationError("No active location found. Import locations/bins before importing sales.")

        bin_obj = self.db.scalar(
            select(Bin)
            .where(
                Bin.tenant_id == tenant_id,
                Bin.location_id == location.id,
                Bin.is_active.is_(True),
                Bin.is_default.is_(True),
            )
            .order_by(Bin.name)
        )
        if bin_obj is None:
            bin_obj = self.db.scalar(
                select(Bin)
                .where(
                    Bin.tenant_id == tenant_id,
                    Bin.location_id == location.id,
                    Bin.is_active.is_(True),
                )
                .order_by(Bin.name)
            )
        if bin_obj is None:
            bin_obj = self.inv_repo.create_bin(tenant_id, location.id, "Main", is_default=True)
        return location, bin_obj

    def _customer_id_for_import(self, tenant_id: uuid.UUID, customer_name: str) -> uuid.UUID | None:
        name = customer_name.strip()
        if not name:
            return None
        existing = [
            customer for customer in self.repo.list_customers(tenant_id, search=name)
            if customer.name.strip().casefold() == name.casefold()
        ]
        if existing:
            return existing[0].id
        customer = self.repo.create_customer(tenant_id=tenant_id, name=name)
        return customer.id

    def _resolve_import_variant(
        self,
        tenant_id: uuid.UUID,
        sku_code: str,
        product_name: str = "",
    ) -> ProductVariant | None:
        exact = self.catalog_repo.get_variant_by_sku(tenant_id, sku_code)
        if exact is not None:
            return exact

        exact_ci = self.db.scalar(
            select(ProductVariant).where(
                ProductVariant.tenant_id == tenant_id,
                ProductVariant.status == "active",
                ProductVariant.sku_code.ilike(sku_code),
            )
        )
        if exact_ci is not None:
            return exact_ci

        parts = [part for part in sku_code.strip().upper().split("-") if part]
        if len(parts) < 3:
            return None

        size_token = parts[-2]
        color_token = parts[-1]
        product_prefix = parts[0]

        candidates = list(
            self.db.scalars(
                select(ProductVariant)
                .join(Size, ProductVariant.size_id == Size.id)
                .join(Color, ProductVariant.color_id == Color.id)
                .join(Product, ProductVariant.product_id == Product.id)
                .where(
                    ProductVariant.tenant_id == tenant_id,
                    ProductVariant.status == "active",
                    Size.tenant_id == tenant_id,
                    Color.tenant_id == tenant_id,
                    Product.tenant_id == tenant_id,
                    Product.status == "active",
                )
                .order_by(Product.product_code, ProductVariant.sku_code)
            )
        )

        matches = [
            variant for variant in candidates
            if self._normalise_code(variant.size.name) == self._normalise_code(size_token)
            and self._color_token_matches(color_token, variant.color.name)
        ]
        if not matches:
            return None

        product_name_norm = self._normalise_code(product_name)
        if product_name_norm:
            named_matches = [
                variant for variant in matches
                if self._normalise_code(variant.product.name) == product_name_norm
            ]
            if len(named_matches) == 1:
                return named_matches[0]
            if not named_matches:
                named_matches = [
                    variant for variant in matches
                    if product_name_norm in self._normalise_code(variant.product.name)
                    or self._normalise_code(variant.product.name) in product_name_norm
                ]
            if len(named_matches) == 1:
                return named_matches[0]
            if len(named_matches) > 1:
                matches = named_matches

        prefix_matches = [
            variant for variant in matches
            if self._normalise_code(variant.product.product_code).startswith(product_prefix)
        ]
        if len(prefix_matches) == 1:
            return prefix_matches[0]
        if len(matches) == 1:
            return matches[0]
        raise ValidationError(
            f"SKU '{sku_code}' matched multiple catalog variants: "
            + ", ".join(variant.sku_code for variant in matches[:5])
        )

    @staticmethod
    def _normalise_code(value: str) -> str:
        return "".join(ch for ch in value.strip().upper() if ch.isalnum())

    @classmethod
    def _color_token_matches(cls, token: str, color_name: str) -> bool:
        token_norm = cls._normalise_code(token)
        color_norm = cls._normalise_code(color_name)
        aliases = {
            "GLD": "GOLD",
            "GLDN": "GOLDEN",
            "GOLD": "GOLDEN",
            "SLV": "SILVER",
            "SLVR": "SILVER",
            "GRN": "GREEN",
            "LNDR": "LAVENDER",
            "LAV": "LAVENDER",
            "YLW": "YELLOW",
            "WHT": "WHITE",
            "BLK": "BLACK",
            "PCH": "PEACH",
        }
        expanded = aliases.get(token_norm, token_norm)
        color_without_vowels = color_norm[:1] + "".join(
            ch for ch in color_norm[1:] if ch not in {"A", "E", "I", "O", "U"}
        )
        possible = {
            color_norm,
            color_norm[:3],
            color_without_vowels,
            color_without_vowels[:3],
        }
        return expanded in possible or token_norm in possible or color_norm.startswith(expanded)

    @staticmethod
    def _norm_header(value: str | None) -> str:
        return (value or "").strip().lower().replace(" ", "_")

    @staticmethod
    def _parse_decimal(value: str, field_name: str) -> Decimal:
        cleaned = value.strip().replace("Rs.", "").replace("₹", "").replace(",", "")
        if not cleaned:
            cleaned = "0"
        try:
            parsed = Decimal(cleaned)
        except Exception as exc:
            raise ValidationError(f"{field_name} must be a number") from exc
        if field_name in {"quantity", "selling_price"} and parsed <= 0:
            raise ValidationError(f"{field_name} must be greater than 0")
        if field_name in {"tax_rate", "discount_amount"} and parsed < 0:
            raise ValidationError(f"{field_name} cannot be negative")
        return parsed

    @staticmethod
    def _parse_date(value: str) -> date:
        raw = value.strip()
        if not raw:
            raise ValidationError("bill_date is required")
        try:
            return date.fromisoformat(raw)
        except ValueError:
            pass
        for fmt in ("%d/%m/%y", "%d/%m/%Y", "%m/%d/%y", "%m/%d/%Y"):
            try:
                from datetime import datetime
                return datetime.strptime(raw, fmt).date()
            except ValueError:
                continue
        raise ValidationError(f"Invalid bill_date '{value}'. Use YYYY-MM-DD.")

    # ── Bill reads ────────────────────────────────────────────────────────────

    def get_bill(self, tenant_id: uuid.UUID, bill_id: uuid.UUID) -> SaleBill:
        self.ensure_sales_tables_available()
        return self.repo.get_bill_by_id(tenant_id, bill_id)

    def list_bills(
        self,
        tenant_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
        customer_id: Optional[uuid.UUID] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> list[SaleBill]:
        self.ensure_sales_tables_available()
        return self.repo.list_bills(
            tenant_id,
            skip=skip,
            limit=limit,
            customer_id=customer_id,
            date_from=date_from,
            date_to=date_to,
        )

    def get_invoice_pdf(
        self, tenant_id: uuid.UUID, bill_id: uuid.UUID, tenant_name: str = "BeHazeld"
    ) -> bytes:
        """
        Retrieve a persisted invoice PDF.  Regenerate on-the-fly if the file
        is missing (e.g. storage was wiped in dev).
        """
        self.ensure_sales_tables_available()
        from pathlib import Path
        from app.core.config import settings

        bill = self.repo.get_bill_by_id(tenant_id, bill_id)
        pdf_path = (
            Path(settings.INVOICE_STORAGE_PATH)
            / str(tenant_id)
            / f"{bill.invoice_number}.pdf"
        )
        if pdf_path.exists():
            return pdf_path.read_bytes()
        # Regenerate and save
        pdf_bytes = report_service.generate_invoice_pdf(bill, tenant_name)
        report_service.save_invoice_pdf(pdf_bytes, tenant_id, bill.invoice_number)
        return pdf_bytes


# ── Internal proxy ────────────────────────────────────────────────────────────

class _LineProxy:
    """Duck-typed SaleBillLine for the PDF renderer (used before DB flush)."""
    def __init__(self, line_req, total: Decimal) -> None:
        self.product_variant_id = line_req.product_variant_id
        self.quantity           = line_req.quantity
        self.selling_price      = line_req.selling_price
        self.discount_amount    = line_req.discount_amount
        self.tax_rate           = line_req.tax_rate
        self.total_line_amount  = total


class _PaymentProxy:
    def __init__(self, payment_req) -> None:
        self.payment_mode  = str(payment_req.payment_mode)
        self.amount        = payment_req.amount
        self.transaction_id = payment_req.transaction_id


class _CustomerProxy:
    def __init__(self, name: str | None) -> None:
        self.name = name or "Walk-in Customer"


class _BillProxy:
    """Duck-typed SaleBill used by generate_invoice_pdf before the ORM object exists."""
    def __init__(
        self,
        invoice_number: str,
        bill_date,
        customer_name: str | None,
        lines_data: list,
        total_amount: Decimal,
        tax_amount: Decimal,
        total_discount: Decimal,
        payment,
    ) -> None:
        self.invoice_number = invoice_number
        self.bill_date      = bill_date
        self.status         = "confirmed"
        self.customer       = _CustomerProxy(customer_name) if customer_name else None
        self.lines          = [_LineProxy(lr, lt) for lr, lt in lines_data]
        self.payments       = [_PaymentProxy(payment)]
        self.total_amount   = total_amount
        self.tax_amount     = tax_amount
        self.total_discount = total_discount
