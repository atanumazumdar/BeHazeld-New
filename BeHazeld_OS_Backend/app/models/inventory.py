"""
Inventory domain models.

Design decisions
----------------
1. MovementType is a Python StrEnum stored as VARCHAR(30).
   SQL Server has no native ENUM type. VARCHAR avoids painful migrations
   when new movement types are added in future phases.

2. StockLedger is append-only (never edited after insert). Every stock
   movement writes one ledger row first; StockBalance is updated in the
   same DB transaction so they are always consistent.

3. bin_id is NOT NULL on Bin, StockBatch, StockLedger, and StockBalance.

   The original Supabase design had bin_id nullable on stock_balances, which
   allowed two rows for the same (variant, warehouse) to coexist when one had
   bin_id = NULL. Because NULL != NULL in SQL uniqueness checks, the composite
   unique constraint was silently bypassed, inflating stock counts.

   Fix: every Location is bootstrapped with a default Bin (is_default=True)
   so every stock movement can always reference a non-NULL bin_id.

4. quantity_change sign convention on StockLedger:
      +  → stock increases  (PURCHASE_IN, RETURN_IN, ADJUSTMENT_IN,
                              TRANSFER_IN, OPENING_STOCK)
      -  → stock decreases  (SALE_OUT, ADJUSTMENT_OUT, TRANSFER_OUT)

5. StockBalance.quantity_available is a computed @property (not stored)
   to avoid three-way consistency problems between on_hand, reserved, and
   available.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    Boolean,
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

_SCHEMA = "inventory"
_QTY = Numeric(14, 4)    # supports fractional units (metres of fabric, rolls, etc.)
_PRICE = Numeric(12, 4)


# ── Movement type enum ────────────────────────────────────────────────────────

class MovementType(StrEnum):
    """
    Classifies every StockLedger entry.

    StrEnum: values ARE strings (no .value needed), safe to store directly
    in a VARCHAR(30) column on SQL Server.
    """
    OPENING_STOCK  = "opening_stock"    # initial stock entry
    PURCHASE_IN    = "purchase_in"      # goods received from supplier
    SALE_OUT       = "sale_out"         # goods sold to customer
    RETURN_IN      = "return_in"        # customer return back to stock
    ADJUSTMENT_IN  = "adjustment_in"    # positive stock adjustment
    ADJUSTMENT_OUT = "adjustment_out"   # negative stock adjustment
    TRANSFER_IN    = "transfer_in"      # received from another location
    TRANSFER_OUT   = "transfer_out"     # sent to another location


# ── Bin ───────────────────────────────────────────────────────────────────────

class Bin(Base):
    """
    A named storage slot inside a Location (shelf, rack, section, zone).

    Every Location must have at least one Bin with is_default=True so that
    every stock movement can always reference a non-NULL bin_id.  The service
    layer creates a 'Main' bin automatically when a Location is created.

    The composite unique constraint (location_id, name) prevents duplicate
    bin names within the same location.
    """

    __tablename__ = "bins"
    __table_args__ = (
        UniqueConstraint("location_id", "name", name="uq_inventory_bins_location_name"),
        Index("ix_inventory_bins_tenant", "tenant_id"),
        Index("ix_inventory_bins_location", "location_id"),
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
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.locations.id", ondelete="NO ACTION"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")

    ledger_entries: Mapped[list[StockLedger]] = relationship(back_populates="bin")
    balances: Mapped[list[StockBalance]] = relationship(back_populates="bin")

    def __repr__(self) -> str:
        return f"<Bin location={self.location_id} name={self.name!r}>"


# ── StockBatch ────────────────────────────────────────────────────────────────

class StockBatch(Base):
    """
    A discrete lot of units received into the warehouse in one event.

    `initial_quantity` is set at receipt and never modified.
    `remaining_quantity` is a denormalised counter updated by the service layer
    on each consumption event.  It is NOT the source of truth (the ledger is),
    but it enables fast low-stock and batch-expiry queries without re-summing
    the ledger.

    `bin_id` is NOT NULL — see module docstring for the rationale.
    `purchase_bill_ref` is populated in Phase 3 (Purchase module); nullable here.
    """

    __tablename__ = "stock_batches"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "batch_number", name="uq_inventory_batches_tenant_number"
        ),
        Index("ix_inventory_batches_tenant_variant", "tenant_id", "product_variant_id"),
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
    product_variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("catalog.product_variants.id", ondelete="NO ACTION"),
        nullable=False,
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.locations.id", ondelete="NO ACTION"),
        nullable=False,
    )
    bin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_SCHEMA}.bins.id", ondelete="NO ACTION"),
        nullable=False,   # NOT NULL — see module docstring
    )

    batch_number: Mapped[str] = mapped_column(String(100), nullable=False)
    initial_quantity: Mapped[Decimal] = mapped_column(_QTY, nullable=False)
    remaining_quantity: Mapped[Decimal] = mapped_column(_QTY, nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(_PRICE, nullable=False)

    purchase_bill_ref: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)

    ledger_entries: Mapped[list[StockLedger]] = relationship(back_populates="batch")

    def __repr__(self) -> str:
        return f"<StockBatch {self.batch_number!r} remaining={self.remaining_quantity}>"


# ── StockLedger ───────────────────────────────────────────────────────────────

class StockLedger(Base):
    """
    One row per stock movement — append-only, NEVER edited after insert.

    `reference_type` / `reference_id` identify the business document that
    caused the movement ("sale_bill" | "purchase_bill" | "adjustment" | …).
    For opening stock these are NULL — there is no originating document.

    `bin_id` is NOT NULL — see module docstring.
    `performed_by_user_id` is nullable (system-generated movements have no user).
    """

    __tablename__ = "stock_ledger"
    __table_args__ = (
        Index(
            "ix_inventory_ledger_tenant_variant_location",
            "tenant_id", "product_variant_id", "location_id",
        ),
        Index("ix_inventory_ledger_reference", "reference_type", "reference_id"),
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
    product_variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("catalog.product_variants.id", ondelete="NO ACTION"),
        nullable=False,
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.locations.id", ondelete="NO ACTION"),
        nullable=False,
    )
    bin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_SCHEMA}.bins.id", ondelete="NO ACTION"),
        nullable=False,   # NOT NULL — see module docstring
    )
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_SCHEMA}.stock_batches.id", ondelete="NO ACTION"),
    )

    movement_type: Mapped[str] = mapped_column(String(30), nullable=False)
    quantity_change: Mapped[Decimal] = mapped_column(_QTY, nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(_PRICE, nullable=False)

    # Originating business document
    reference_type: Mapped[str | None] = mapped_column(String(50))
    reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    notes: Mapped[str | None] = mapped_column(Text)
    performed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity.users.id", ondelete="NO ACTION"),
    )

    bin: Mapped[Bin] = relationship(back_populates="ledger_entries")
    batch: Mapped[StockBatch | None] = relationship(back_populates="ledger_entries")


# ── StockBalance ──────────────────────────────────────────────────────────────

class StockBalance(Base):
    """
    Running aggregate for one (tenant, variant, location, bin) position.

    One row per unique combination — enforced by the composite unique constraint
    `uq_inventory_balance_variant_location_bin`.

    Updated transactionally alongside every StockLedger write so they are
    always consistent.  This is NOT the source of truth — the ledger is.

    `quantity_available` is a computed @property (on_hand - reserved). It is
    NOT stored as a column to avoid three-way consistency problems.

    bin_id NOT NULL design rationale
    ---------------------------------
    The original Supabase design used a nullable bin_id. Because NULL != NULL
    in SQL Server uniqueness checks, two rows for the same (variant, warehouse)
    could coexist when one had bin_id = NULL, silently inflating stock counts.
    Making bin_id NOT NULL (always referencing the location's default Bin) makes
    the composite unique constraint work reliably.
    """

    __tablename__ = "stock_balances"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "product_variant_id", "location_id", "bin_id",
            name="uq_inventory_balance_variant_location_bin",
        ),
        Index("ix_inventory_balance_tenant_variant", "tenant_id", "product_variant_id"),
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
    product_variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("catalog.product_variants.id", ondelete="NO ACTION"),
        nullable=False,
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.locations.id", ondelete="NO ACTION"),
        nullable=False,
    )
    bin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_SCHEMA}.bins.id", ondelete="NO ACTION"),
        nullable=False,   # NOT NULL — see class docstring
    )

    quantity_on_hand: Mapped[Decimal] = mapped_column(
        _QTY, nullable=False, server_default="0"
    )
    quantity_reserved: Mapped[Decimal] = mapped_column(
        _QTY, nullable=False, server_default="0"
    )

    bin: Mapped[Bin] = relationship(back_populates="balances")

    @property
    def quantity_available(self) -> Decimal:
        """Computed: on_hand minus reserved. Not stored — avoids three-way sync problems."""
        return self.quantity_on_hand - self.quantity_reserved

    def __repr__(self) -> str:
        return (
            f"<StockBalance variant={self.product_variant_id} "
            f"on_hand={self.quantity_on_hand} reserved={self.quantity_reserved}>"
        )
