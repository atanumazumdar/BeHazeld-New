"""
PurchaseService — atomic procurement engine.

create_purchase_bill() executes one database transaction that:

  1. Validates vendor exists (raises NotFoundError if not)
  2. Validates every product variant in the lines (raises NotFoundError on
     the first invalid SKU — the entire bill is aborted)
  3. Computes line totals and bill-level aggregates (total_amount, tax_amount)
  4. Creates the PurchaseBill header (status: confirmed)
  5. For each line:
     a. Creates PurchaseBillLine
     b. Appends a StockLedger entry (PURCHASE_IN, positive quantity_change)
        via InventoryRepository (no intermediate commit — atomicity preserved)
     c. Creates a StockBatch referencing this bill's bill_number
     d. Upserts StockBalance
  6. Commits once — if anything in steps 1-5 raises, rollback() is called
     and nothing is persisted.

Why InventoryRepository directly (not InventoryService)?
---------------------------------------------------------
InventoryService.record_stock_movement() commits internally. Calling it N
times for N lines would produce N separate commits, making it impossible to
roll back the whole bill atomically. By calling InventoryRepository methods
directly (same Session, same transaction) we control the single commit point.
"""
import uuid
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.base import Base
from app.models.inventory import MovementType
from app.models.purchase import PurchaseBill, PurchaseBillLine, Transporter, Vendor, VendorPayment
from app.repositories.catalog_repository import CatalogRepository
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.purchase_repository import PurchaseRepository
from app.schemas.purchase import (
    CreatePurchaseBillRequest,
    CreateTransporterRequest,
    CreateVendorRequest,
    RecordVendorPaymentRequest,
)


class PurchaseService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = PurchaseRepository(db)
        self.inv_repo = InventoryRepository(db)
        self.catalog_repo = CatalogRepository(db)
        self._finance_svc = None   # injected lazily; None → skip journal posting

    def ensure_purchase_tables_available(self) -> None:
        """Create purchase schema tables on first-run production databases."""
        bind = self.db.get_bind()
        dialect_name = getattr(getattr(bind, "dialect", None), "name", None)
        if dialect_name != "postgresql":
            return

        with bind.begin() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS purchase"))

        Base.metadata.create_all(
            bind=bind,
            tables=[
                Vendor.__table__,
                Transporter.__table__,
                PurchaseBill.__table__,
                PurchaseBillLine.__table__,
                VendorPayment.__table__,
            ],
        )

    # ── Vendor management ─────────────────────────────────────────────────────

    def create_vendor(self, tenant_id: uuid.UUID, req: CreateVendorRequest) -> Vendor:
        self.ensure_purchase_tables_available()
        try:
            vendor = self.repo.create_vendor(
                tenant_id=tenant_id,
                name=req.name,
                gstin=req.gstin,
                address=req.address,
                contact_name=req.contact_name,
                contact_phone=req.contact_phone,
                contact_email=req.contact_email,
            )
            self.db.commit()
            self.db.refresh(vendor)
            return vendor
        except Exception:
            self.db.rollback()
            raise

    def list_vendors(self, tenant_id: uuid.UUID) -> list[Vendor]:
        self.ensure_purchase_tables_available()
        return self.repo.list_vendors(tenant_id)

    def create_transporter(self, tenant_id: uuid.UUID, req: CreateTransporterRequest):
        self.ensure_purchase_tables_available()
        try:
            t = self.repo.create_transporter(
                tenant_id=tenant_id,
                name=req.name,
                vehicle_no=req.vehicle_no,
                contact_phone=req.contact_phone,
            )
            self.db.commit()
            self.db.refresh(t)
            return t
        except Exception:
            self.db.rollback()
            raise

    # ── Purchase bill — ATOMIC ────────────────────────────────────────────────

    def create_purchase_bill(
        self,
        tenant_id: uuid.UUID,
        req: CreatePurchaseBillRequest,
        performed_by_user_id: uuid.UUID | None = None,
    ) -> PurchaseBill:
        """
        Create a confirmed purchase bill and record stock movements atomically.

        Raises
        ------
        NotFoundError   — vendor or any product variant not found for this tenant
        ConflictError   — bill_number already exists for this tenant

        On any exception the full transaction is rolled back: no bill, no
        ledger entries, no batch records, no balance changes are persisted.
        """
        self.ensure_purchase_tables_available()
        try:
            # ── Step 1: validate vendor ───────────────────────────────────────
            self.repo.get_vendor_by_id(tenant_id, req.vendor_id)  # raises NotFoundError

            # ── Step 2: validate ALL variants before writing anything ─────────
            variants: list = []
            for line_req in req.lines:
                # get_variant_by_id raises NotFoundError if missing
                variant = self.catalog_repo.get_variant_by_id(
                    tenant_id, line_req.product_variant_id
                )
                variants.append(variant)

            # ── Step 3: compute totals ────────────────────────────────────────
            total_amount = Decimal("0")
            tax_amount = Decimal("0")
            line_totals: list[Decimal] = []

            for line_req in req.lines:
                line_total = (line_req.quantity * line_req.unit_cost * (
                    1 + line_req.tax_rate
                )).quantize(Decimal("0.01"))
                line_tax = (line_req.quantity * line_req.unit_cost * line_req.tax_rate
                            ).quantize(Decimal("0.01"))
                line_totals.append(line_total)
                total_amount += line_total
                tax_amount += line_tax

            # ── Step 4: create bill header ────────────────────────────────────
            bill = self.repo.create_bill(
                tenant_id=tenant_id,
                vendor_id=req.vendor_id,
                location_id=req.location_id,
                bin_id=req.bin_id,
                bill_number=req.bill_number,
                bill_date=req.bill_date,
                total_amount=total_amount,
                tax_amount=tax_amount,
                transporter_id=req.transporter_id,
                notes=req.notes,
            )

            # ── Step 5: lines + stock movements ──────────────────────────────
            for line_req, variant, line_total in zip(req.lines, variants, line_totals):
                # 5a — create bill line
                self.repo.create_bill_line(
                    tenant_id=tenant_id,
                    bill_id=bill.id,
                    product_variant_id=line_req.product_variant_id,
                    quantity=line_req.quantity,
                    unit_cost=line_req.unit_cost,
                    tax_rate=line_req.tax_rate,
                    total_line_amount=line_total,
                )

                # 5b — append ledger entry (no commit — same transaction)
                ledger_entry = self.inv_repo.append_ledger_entry(
                    tenant_id=tenant_id,
                    product_variant_id=line_req.product_variant_id,
                    location_id=req.location_id,
                    bin_id=req.bin_id,
                    movement_type=MovementType.PURCHASE_IN,
                    quantity_change=line_req.quantity,   # positive — inward
                    unit_cost=line_req.unit_cost,
                    reference_type="purchase_bill",
                    reference_id=bill.id,
                    notes=f"Purchase bill {req.bill_number}",
                    performed_by_user_id=performed_by_user_id,
                )

                # 5c — create stock batch referencing this bill
                batch_number = line_req.batch_number or str(ledger_entry.id)
                self.inv_repo.create_batch(
                    tenant_id=tenant_id,
                    product_variant_id=line_req.product_variant_id,
                    location_id=req.location_id,
                    bin_id=req.bin_id,
                    batch_number=batch_number,
                    initial_quantity=line_req.quantity,
                    unit_cost=line_req.unit_cost,
                    purchase_bill_ref=req.bill_number,
                )

                # 5d — upsert balance (+qty)
                self.inv_repo.upsert_balance(
                    tenant_id=tenant_id,
                    product_variant_id=line_req.product_variant_id,
                    location_id=req.location_id,
                    bin_id=req.bin_id,
                    quantity_delta=line_req.quantity,
                )

            # ── Step 6: post accounting journal (same transaction) ───────────
            if self._finance_svc is not None:
                self._finance_svc.post_purchase_journal(
                    tenant_id=tenant_id,
                    ref_id=bill.id,
                    entry_date=req.bill_date,
                    total_amount=total_amount,
                )

            # ── Step 7: single commit ─────────────────────────────────────────
            self.db.commit()
            self.db.refresh(bill)
            return bill

        except Exception:
            self.db.rollback()
            raise

    # ── Bill reads ────────────────────────────────────────────────────────────

    def get_bill(self, tenant_id: uuid.UUID, bill_id: uuid.UUID) -> PurchaseBill:
        self.ensure_purchase_tables_available()
        return self.repo.get_bill_by_id(tenant_id, bill_id)

    def list_bills(
        self, tenant_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> list[PurchaseBill]:
        self.ensure_purchase_tables_available()
        return self.repo.list_bills(tenant_id, skip=skip, limit=limit)

    # ── Payments ──────────────────────────────────────────────────────────────

    def record_payment(
        self, tenant_id: uuid.UUID, req: RecordVendorPaymentRequest
    ) -> VendorPayment:
        self.ensure_purchase_tables_available()
        try:
            # Validate bill belongs to tenant
            self.repo.get_bill_by_id(tenant_id, req.bill_id)  # raises NotFoundError

            payment = self.repo.create_payment(
                tenant_id=tenant_id,
                bill_id=req.bill_id,
                payment_date=req.payment_date,
                amount=req.amount,
                payment_mode=req.payment_mode,
                reference_number=req.reference_number,
                notes=req.notes,
            )
            self.db.commit()
            self.db.refresh(payment)
            return payment
        except Exception:
            self.db.rollback()
            raise
