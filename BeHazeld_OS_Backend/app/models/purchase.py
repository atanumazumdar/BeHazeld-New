"""
Purchase domain models.

Entity hierarchy
----------------
Vendor ──────────────────────────────────┐
Transporter ──────────────────────────── PurchaseBill ──► PurchaseBillLine
                                                  │
                                                  └──► VendorPayment

Design decisions
----------------
* All PKs use PostgreSQL UUID columns with ORM-generated values.
* Every table scoped by tenant_id.
* PurchaseBill.status: "draft" | "confirmed" | "cancelled"
  - "draft"     → editable, no stock movement yet
  - "confirmed" → stock movements recorded, immutable lines
  - "cancelled" → soft-cancelled, no stock adjustment reversal in this phase
* PurchaseBillLine.total_line_amount is a stored computed column (qty * unit_cost)
  to avoid recalculation; updated by the service on write.
* VendorPayment is linked to PurchaseBill (not Vendor directly) so partial
  payments against a bill are naturally modelled.
* PaymentMode uses VARCHAR("cash"|"bank_transfer"|"cheque"|"upi"|"other").
* purchase_bill_ref on StockBatch (in inventory schema) is populated by the
  service so batches trace back to their originating bill.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    Date,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

_SCHEMA = "purchase"
_AMT = Numeric(14, 2)   # monetary amounts: 2 decimal places
_QTY = Numeric(14, 4)   # quantities: 4 decimal places (fabrics, etc.)
_TAX = Numeric(6, 4)    # tax rate: e.g. 0.1800 = 18 %


class PaymentMode(StrEnum):
    CASH          = "cash"
    BANK_TRANSFER = "bank_transfer"
    CHEQUE        = "cheque"
    UPI           = "upi"
    OTHER         = "other"


class BillStatus(StrEnum):
    DRAFT      = "draft"
    CONFIRMED  = "confirmed"
    CANCELLED  = "cancelled"


# ── Vendor ────────────────────────────────────────────────────────────────────

class Vendor(Base):
    """
    A goods supplier.

    GSTIN is the Indian GST Identification Number — nullable for vendors
    not registered under GST (e.g. small traders under composition scheme).
    """

    __tablename__ = "vendors"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_purchase_vendors_tenant_name"),
        Index("ix_purchase_vendors_tenant", "tenant_id"),
        {"schema": _SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    gstin: Mapped[str | None] = mapped_column(String(20))
    address: Mapped[str | None] = mapped_column(Text)
    contact_name: Mapped[str | None] = mapped_column(String(150))
    contact_phone: Mapped[str | None] = mapped_column(String(20))
    contact_email: Mapped[str | None] = mapped_column(String(254))
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default="1")

    bills: Mapped[list[PurchaseBill]] = relationship(back_populates="vendor")

    def __repr__(self) -> str:
        return f"<Vendor {self.name!r}>"


# ── Transporter ───────────────────────────────────────────────────────────────

class Transporter(Base):
    """Logistics company or vehicle that delivered the goods."""

    __tablename__ = "transporters"
    __table_args__ = (
        Index("ix_purchase_transporters_tenant", "tenant_id"),
        {"schema": _SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    vehicle_no: Mapped[str | None] = mapped_column(String(50))
    contact_phone: Mapped[str | None] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default="1")

    bills: Mapped[list[PurchaseBill]] = relationship(back_populates="transporter")

    def __repr__(self) -> str:
        return f"<Transporter {self.name!r}>"


# ── PurchaseBill ──────────────────────────────────────────────────────────────

class PurchaseBill(Base):
    """
    Header record for one purchase from a vendor.

    `bill_number` is the vendor's invoice number (tenant-unique).
    `total_amount` = sum of all line totals (incl. tax).
    `tax_amount`   = sum of all line tax amounts.
    Status lifecycle: draft → confirmed (immutable) or cancelled.
    """

    __tablename__ = "purchase_bills"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "bill_number",
            name="uq_purchase_bills_tenant_number",
        ),
        Index("ix_purchase_bills_tenant", "tenant_id"),
        Index("ix_purchase_bills_vendor", "vendor_id"),
        {"schema": _SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_SCHEMA}.vendors.id", ondelete="NO ACTION"),
        nullable=False,
    )
    transporter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_SCHEMA}.transporters.id", ondelete="SET NULL"),
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.locations.id", ondelete="NO ACTION"),
        nullable=False,
        comment="Receiving warehouse/location",
    )
    bin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inventory.bins.id", ondelete="NO ACTION"),
        nullable=False,
        comment="Receiving bin within the location",
    )

    bill_number: Mapped[str] = mapped_column(String(100), nullable=False)
    bill_date: Mapped[str] = mapped_column(Date, nullable=False)  # stored as date
    total_amount: Mapped[Decimal] = mapped_column(_AMT, nullable=False, server_default="0")
    tax_amount: Mapped[Decimal] = mapped_column(_AMT, nullable=False, server_default="0")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="'draft'"
    )
    notes: Mapped[str | None] = mapped_column(Text)

    vendor: Mapped[Vendor] = relationship(back_populates="bills")
    transporter: Mapped[Transporter | None] = relationship(back_populates="bills")
    lines: Mapped[list[PurchaseBillLine]] = relationship(
        back_populates="bill", cascade="all, delete-orphan"
    )
    payments: Mapped[list[VendorPayment]] = relationship(
        back_populates="bill", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<PurchaseBill {self.bill_number!r} status={self.status}>"


# ── PurchaseBillLine ──────────────────────────────────────────────────────────

class PurchaseBillLine(Base):
    """
    One line item on a PurchaseBill — one SKU per line.

    `total_line_amount` = quantity * unit_cost * (1 + tax_rate)
    The service computes and stores this so reporting queries never
    need to recalculate.
    """

    __tablename__ = "purchase_bill_lines"
    __table_args__ = (
        UniqueConstraint(
            "bill_id", "product_variant_id",
            name="uq_purchase_lines_bill_variant",
        ),
        Index("ix_purchase_lines_bill", "bill_id"),
        Index("ix_purchase_lines_variant", "product_variant_id"),
        {"schema": _SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    bill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_SCHEMA}.purchase_bills.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("catalog.product_variants.id", ondelete="NO ACTION"),
        nullable=False,
    )

    quantity: Mapped[Decimal] = mapped_column(_QTY, nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(_AMT, nullable=False)
    tax_rate: Mapped[Decimal] = mapped_column(_TAX, nullable=False, server_default="0")
    total_line_amount: Mapped[Decimal] = mapped_column(_AMT, nullable=False)

    bill: Mapped[PurchaseBill] = relationship(back_populates="lines")

    def __repr__(self) -> str:
        return (
            f"<PurchaseBillLine variant={self.product_variant_id} "
            f"qty={self.quantity} cost={self.unit_cost}>"
        )


# ── VendorPayment ─────────────────────────────────────────────────────────────

class VendorPayment(Base):
    """
    A single payment made against a PurchaseBill.

    Multiple partial payments are supported — sum of all VendorPayment.amount
    for a bill gives total paid. Remaining = bill.total_amount - total_paid.
    """

    __tablename__ = "vendor_payments"
    __table_args__ = (
        Index("ix_purchase_payments_bill", "bill_id"),
        Index("ix_purchase_payments_tenant", "tenant_id"),
        {"schema": _SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    bill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_SCHEMA}.purchase_bills.id", ondelete="CASCADE"),
        nullable=False,
    )

    payment_date: Mapped[str] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(_AMT, nullable=False)
    payment_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    reference_number: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)

    bill: Mapped[PurchaseBill] = relationship(back_populates="payments")

    def __repr__(self) -> str:
        return f"<VendorPayment {self.payment_mode} ₹{self.amount}>"
