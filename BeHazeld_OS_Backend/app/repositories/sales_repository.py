"""
Sales repository — pure data access layer for the sales schema.

Rule: every method receives tenant_id as its first argument and uses it
as the primary WHERE filter. No business logic here.

Invoice number generation
-------------------------
generate_invoice_number(seq) is a pure function used by the service layer.
Format: INV-{seq:06d}  e.g. INV-000001, INV-000042
"""
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from typing import Optional

from app.core.exceptions import ConflictError, NotFoundError
from app.models.sales import Customer, SaleBill, SaleBillLine, SalePayment


def generate_invoice_number(seq: int) -> str:
    """Pure function — deterministic, no DB calls. Called by the service."""
    return f"INV-{seq:06d}"


class SalesRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Customer ──────────────────────────────────────────────────────────────

    def create_customer(
        self,
        tenant_id: uuid.UUID,
        name: str,
        email: str | None = None,
        phone: str | None = None,
        address: str | None = None,
    ) -> Customer:
        obj = Customer(
            tenant_id=tenant_id,
            name=name,
            email=email,
            phone=phone,
            address=address,
            loyalty_points=0,
            is_active=True,
        )
        self.db.add(obj)
        self.db.flush()
        return obj

    def get_customer_by_id(
        self, tenant_id: uuid.UUID, customer_id: uuid.UUID
    ) -> Customer:
        c = self.db.scalar(
            select(Customer).where(
                Customer.tenant_id == tenant_id,
                Customer.id == customer_id,
                Customer.is_active.is_(True),
            )
        )
        if c is None:
            raise NotFoundError(f"Customer {customer_id} not found")
        return c

    def list_customers(
        self, tenant_id: uuid.UUID, search: Optional[str] = None
    ) -> list[Customer]:
        q = select(Customer).where(
            Customer.tenant_id == tenant_id, Customer.is_active.is_(True)
        )
        if search:
            pattern = f"%{search}%"
            q = q.where(
                Customer.name.ilike(pattern) | Customer.phone.ilike(pattern)
            )
        return list(self.db.scalars(q.order_by(Customer.name)))

    # ── SaleBill ──────────────────────────────────────────────────────────────

    def count_bills_by_tenant(self, tenant_id: uuid.UUID) -> int:
        result = self.db.scalar(
            select(func.count()).select_from(SaleBill).where(
                SaleBill.tenant_id == tenant_id
            )
        )
        return result or 0

    def get_bill_by_invoice_number(
        self, tenant_id: uuid.UUID, invoice_number: str
    ) -> SaleBill | None:
        return self.db.scalar(
            select(SaleBill).where(
                SaleBill.tenant_id == tenant_id,
                SaleBill.invoice_number == invoice_number,
            )
        )

    def create_bill(
        self,
        tenant_id: uuid.UUID,
        invoice_number: str,
        bill_date: date,
        location_id: uuid.UUID,
        bin_id: uuid.UUID,
        total_amount: Decimal,
        tax_amount: Decimal,
        total_discount: Decimal,
        customer_id: uuid.UUID | None = None,
        notes: str | None = None,
    ) -> SaleBill:
        if self.get_bill_by_invoice_number(tenant_id, invoice_number) is not None:
            raise ConflictError(f"Invoice '{invoice_number}' already exists")
        bill = SaleBill(
            tenant_id=tenant_id,
            invoice_number=invoice_number,
            bill_date=bill_date,
            location_id=location_id,
            bin_id=bin_id,
            total_amount=total_amount,
            tax_amount=tax_amount,
            total_discount=total_discount,
            customer_id=customer_id,
            notes=notes,
            status="confirmed",
        )
        self.db.add(bill)
        self.db.flush()
        return bill

    def get_bill_by_id(self, tenant_id: uuid.UUID, bill_id: uuid.UUID) -> SaleBill:
        bill = self.db.scalar(
            select(SaleBill).where(
                SaleBill.tenant_id == tenant_id,
                SaleBill.id == bill_id,
            )
        )
        if bill is None:
            raise NotFoundError(f"SaleBill {bill_id} not found")
        return bill

    def list_bills(
        self,
        tenant_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
        customer_id: Optional[uuid.UUID] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> list[SaleBill]:
        q = select(SaleBill).where(SaleBill.tenant_id == tenant_id)
        if customer_id is not None:
            q = q.where(SaleBill.customer_id == customer_id)
        if date_from is not None:
            q = q.where(SaleBill.bill_date >= date_from)
        if date_to is not None:
            q = q.where(SaleBill.bill_date <= date_to)
        return list(
            self.db.scalars(
                q.order_by(SaleBill.bill_date.desc()).offset(skip).limit(limit)
            )
        )

    # ── SaleBillLine ──────────────────────────────────────────────────────────

    def create_bill_line(
        self,
        tenant_id: uuid.UUID,
        bill_id: uuid.UUID,
        product_variant_id: uuid.UUID,
        quantity: Decimal,
        selling_price: Decimal,
        unit_cost: Decimal,
        tax_rate: Decimal,
        discount_amount: Decimal,
        total_line_amount: Decimal,
    ) -> SaleBillLine:
        line = SaleBillLine(
            tenant_id=tenant_id,
            bill_id=bill_id,
            product_variant_id=product_variant_id,
            quantity=quantity,
            selling_price=selling_price,
            unit_cost=unit_cost,
            tax_rate=tax_rate,
            discount_amount=discount_amount,
            total_line_amount=total_line_amount,
        )
        self.db.add(line)
        self.db.flush()
        return line

    # ── SalePayment ───────────────────────────────────────────────────────────

    def create_payment(
        self,
        tenant_id: uuid.UUID,
        bill_id: uuid.UUID,
        payment_date: date,
        amount: Decimal,
        payment_mode: str,
        transaction_id: str | None = None,
        notes: str | None = None,
    ) -> SalePayment:
        payment = SalePayment(
            tenant_id=tenant_id,
            bill_id=bill_id,
            payment_date=payment_date,
            amount=amount,
            payment_mode=payment_mode,
            transaction_id=transaction_id,
            notes=notes,
        )
        self.db.add(payment)
        self.db.flush()
        return payment
