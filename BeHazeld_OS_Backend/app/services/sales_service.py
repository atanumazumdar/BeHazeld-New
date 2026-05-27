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
import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, StockNotAvailableError
from app.models.inventory import MovementType
from app.models.sales import Customer, SaleBill, SalePayment
from app.repositories.catalog_repository import CatalogRepository
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.sales_repository import SalesRepository, generate_invoice_number
from app.schemas.sales import (
    CreateCustomerRequest,
    CreateSaleBillRequest,
    InvoiceMetadata,
    SaleBillResponse,
)
from app.services import report_service


class SalesService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = SalesRepository(db)
        self.inv_repo = InventoryRepository(db)
        self.catalog_repo = CatalogRepository(db)
        self._finance_svc = None   # injected lazily; None → skip journal posting

    # ── Customer management ───────────────────────────────────────────────────

    def create_customer(
        self, tenant_id: uuid.UUID, req: CreateCustomerRequest
    ) -> Customer:
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
        return self.repo.list_customers(tenant_id, search=search)

    def get_customer(self, tenant_id: uuid.UUID, customer_id: uuid.UUID) -> Customer:
        return self.repo.get_customer_by_id(tenant_id, customer_id)

    # ── The main sales transaction ────────────────────────────────────────────

    def create_sale(
        self,
        tenant_id: uuid.UUID,
        req: CreateSaleBillRequest,
        tenant_name: str = "BeHazeld",
        performed_by_user_id: uuid.UUID | None = None,
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
            pdf_bytes = report_service.generate_invoice_pdf(bill_proxy, tenant_name)

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
        metadata = report_service.save_invoice_pdf(pdf_bytes, tenant_id, invoice_number)
        return bill, metadata

    # ── Bill reads ────────────────────────────────────────────────────────────

    def get_bill(self, tenant_id: uuid.UUID, bill_id: uuid.UUID) -> SaleBill:
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
