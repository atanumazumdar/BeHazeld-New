"""
Purchase repository — pure data access layer for the purchase schema.

Rule: every method receives tenant_id as its first argument and uses it
as the primary WHERE filter. No business logic lives here.
"""
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.purchase import (
    BillStatus,
    PaymentMode,
    PurchaseBill,
    PurchaseBillLine,
    Transporter,
    Vendor,
    VendorPayment,
)


class PurchaseRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Vendor ────────────────────────────────────────────────────────────────

    def create_vendor(
        self,
        tenant_id: uuid.UUID,
        name: str,
        gstin: str | None = None,
        address: str | None = None,
        contact_name: str | None = None,
        contact_phone: str | None = None,
        contact_email: str | None = None,
    ) -> Vendor:
        obj = Vendor(
            tenant_id=tenant_id,
            name=name,
            gstin=gstin,
            address=address,
            contact_name=contact_name,
            contact_phone=contact_phone,
            contact_email=contact_email,
            is_active=True,
        )
        self.db.add(obj)
        self.db.flush()
        return obj

    def get_vendor_by_id(self, tenant_id: uuid.UUID, vendor_id: uuid.UUID) -> Vendor:
        vendor = self.db.scalar(
            select(Vendor).where(
                Vendor.tenant_id == tenant_id,
                Vendor.id == vendor_id,
                Vendor.is_active.is_(True),
            )
        )
        if vendor is None:
            raise NotFoundError(f"Vendor {vendor_id} not found")
        return vendor

    def list_vendors(self, tenant_id: uuid.UUID) -> list[Vendor]:
        return list(
            self.db.scalars(
                select(Vendor)
                .where(Vendor.tenant_id == tenant_id, Vendor.is_active.is_(True))
                .order_by(Vendor.name)
            )
        )

    # ── Transporter ───────────────────────────────────────────────────────────

    def create_transporter(
        self,
        tenant_id: uuid.UUID,
        name: str,
        vehicle_no: str | None = None,
        contact_phone: str | None = None,
    ) -> Transporter:
        obj = Transporter(
            tenant_id=tenant_id,
            name=name,
            vehicle_no=vehicle_no,
            contact_phone=contact_phone,
            is_active=True,
        )
        self.db.add(obj)
        self.db.flush()
        return obj

    def get_transporter_by_id(
        self, tenant_id: uuid.UUID, transporter_id: uuid.UUID
    ) -> Transporter:
        t = self.db.scalar(
            select(Transporter).where(
                Transporter.tenant_id == tenant_id,
                Transporter.id == transporter_id,
            )
        )
        if t is None:
            raise NotFoundError(f"Transporter {transporter_id} not found")
        return t

    # ── PurchaseBill ──────────────────────────────────────────────────────────

    def get_bill_by_number(
        self, tenant_id: uuid.UUID, bill_number: str
    ) -> PurchaseBill | None:
        return self.db.scalar(
            select(PurchaseBill).where(
                PurchaseBill.tenant_id == tenant_id,
                PurchaseBill.bill_number == bill_number,
            )
        )

    def create_bill(
        self,
        tenant_id: uuid.UUID,
        vendor_id: uuid.UUID,
        location_id: uuid.UUID,
        bin_id: uuid.UUID,
        bill_number: str,
        bill_date: date,
        total_amount: Decimal,
        tax_amount: Decimal,
        transporter_id: uuid.UUID | None = None,
        notes: str | None = None,
    ) -> PurchaseBill:
        if self.get_bill_by_number(tenant_id, bill_number) is not None:
            raise ConflictError(f"Purchase bill '{bill_number}' already exists")
        bill = PurchaseBill(
            tenant_id=tenant_id,
            vendor_id=vendor_id,
            location_id=location_id,
            bin_id=bin_id,
            bill_number=bill_number,
            bill_date=bill_date,
            total_amount=total_amount,
            tax_amount=tax_amount,
            transporter_id=transporter_id,
            notes=notes,
            status=BillStatus.CONFIRMED,  # confirmed immediately on creation
        )
        self.db.add(bill)
        self.db.flush()
        return bill

    def get_bill_by_id(self, tenant_id: uuid.UUID, bill_id: uuid.UUID) -> PurchaseBill:
        bill = self.db.scalar(
            select(PurchaseBill).where(
                PurchaseBill.tenant_id == tenant_id,
                PurchaseBill.id == bill_id,
            )
        )
        if bill is None:
            raise NotFoundError(f"PurchaseBill {bill_id} not found")
        return bill

    def list_bills(
        self,
        tenant_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> list[PurchaseBill]:
        return list(
            self.db.scalars(
                select(PurchaseBill)
                .where(PurchaseBill.tenant_id == tenant_id)
                .order_by(PurchaseBill.bill_date.desc())
                .offset(skip)
                .limit(limit)
            )
        )

    # ── PurchaseBillLine ──────────────────────────────────────────────────────

    def create_bill_line(
        self,
        tenant_id: uuid.UUID,
        bill_id: uuid.UUID,
        product_variant_id: uuid.UUID,
        quantity: Decimal,
        unit_cost: Decimal,
        tax_rate: Decimal,
        total_line_amount: Decimal,
    ) -> PurchaseBillLine:
        line = PurchaseBillLine(
            tenant_id=tenant_id,
            bill_id=bill_id,
            product_variant_id=product_variant_id,
            quantity=quantity,
            unit_cost=unit_cost,
            tax_rate=tax_rate,
            total_line_amount=total_line_amount,
        )
        self.db.add(line)
        self.db.flush()
        return line

    # ── VendorPayment ─────────────────────────────────────────────────────────

    def create_payment(
        self,
        tenant_id: uuid.UUID,
        bill_id: uuid.UUID,
        payment_date: date,
        amount: Decimal,
        payment_mode: PaymentMode,
        reference_number: str | None = None,
        notes: str | None = None,
    ) -> VendorPayment:
        payment = VendorPayment(
            tenant_id=tenant_id,
            bill_id=bill_id,
            payment_date=payment_date,
            amount=amount,
            payment_mode=str(payment_mode),
            reference_number=reference_number,
            notes=notes,
        )
        self.db.add(payment)
        self.db.flush()
        return payment

    def list_payments_by_bill(
        self, tenant_id: uuid.UUID, bill_id: uuid.UUID
    ) -> list[VendorPayment]:
        return list(
            self.db.scalars(
                select(VendorPayment).where(
                    VendorPayment.tenant_id == tenant_id,
                    VendorPayment.bill_id == bill_id,
                ).order_by(VendorPayment.payment_date)
            )
        )
