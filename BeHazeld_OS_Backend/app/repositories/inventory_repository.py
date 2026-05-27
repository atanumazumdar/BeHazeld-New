"""
Inventory repository — pure data access layer for the inventory schema.

Rule: every method receives tenant_id as its first argument and uses it as
the primary WHERE filter. No business logic lives here.

StockLedger is append-only: append_ledger_entry only calls db.add() + flush(),
never updates an existing row.

upsert_balance uses a select-then-write pattern (not SQL MERGE) for
compatibility with synchronous SQLAlchemy sessions.
"""
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.inventory import Bin, MovementType, StockBalance, StockBatch, StockLedger


class InventoryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Bin ───────────────────────────────────────────────────────────────────

    def create_bin(
        self,
        tenant_id: uuid.UUID,
        location_id: uuid.UUID,
        name: str,
        is_default: bool = False,
    ) -> Bin:
        b = Bin(
            tenant_id=tenant_id,
            location_id=location_id,
            name=name,
            is_default=is_default,
            is_active=True,
        )
        self.db.add(b)
        self.db.flush()
        return b

    def get_bin(self, tenant_id: uuid.UUID, bin_id: uuid.UUID) -> Bin:
        b = self.db.scalar(
            select(Bin).where(Bin.tenant_id == tenant_id, Bin.id == bin_id)
        )
        if b is None:
            raise NotFoundError(f"Bin {bin_id} not found")
        return b

    def get_default_bin(self, tenant_id: uuid.UUID, location_id: uuid.UUID) -> Bin:
        b = self.db.scalar(
            select(Bin).where(
                Bin.tenant_id == tenant_id,
                Bin.location_id == location_id,
                Bin.is_default.is_(True),
                Bin.is_active.is_(True),
            )
        )
        if b is None:
            raise NotFoundError(
                f"No default bin found for location {location_id}"
            )
        return b

    def list_bins_by_location(
        self, tenant_id: uuid.UUID, location_id: uuid.UUID
    ) -> list[Bin]:
        return list(
            self.db.scalars(
                select(Bin).where(
                    Bin.tenant_id == tenant_id,
                    Bin.location_id == location_id,
                    Bin.is_active.is_(True),
                ).order_by(Bin.name)
            )
        )

    # ── StockBatch ────────────────────────────────────────────────────────────

    def create_batch(
        self,
        tenant_id: uuid.UUID,
        product_variant_id: uuid.UUID,
        location_id: uuid.UUID,
        bin_id: uuid.UUID,
        batch_number: str,
        initial_quantity: Decimal,
        unit_cost: Decimal,
        purchase_bill_ref: str | None = None,
        notes: str | None = None,
    ) -> StockBatch:
        batch = StockBatch(
            tenant_id=tenant_id,
            product_variant_id=product_variant_id,
            location_id=location_id,
            bin_id=bin_id,
            batch_number=batch_number,
            initial_quantity=initial_quantity,
            remaining_quantity=initial_quantity,  # starts full
            unit_cost=unit_cost,
            purchase_bill_ref=purchase_bill_ref,
            notes=notes,
        )
        self.db.add(batch)
        self.db.flush()
        return batch

    def get_batch(self, tenant_id: uuid.UUID, batch_id: uuid.UUID) -> StockBatch:
        batch = self.db.scalar(
            select(StockBatch).where(
                StockBatch.tenant_id == tenant_id,
                StockBatch.id == batch_id,
            )
        )
        if batch is None:
            raise NotFoundError(f"StockBatch {batch_id} not found")
        return batch

    def decrement_batch_remaining(
        self,
        tenant_id: uuid.UUID,
        batch_id: uuid.UUID,
        quantity: Decimal,
    ) -> StockBatch:
        batch = self.get_batch(tenant_id, batch_id)
        batch.remaining_quantity -= quantity
        self.db.flush()
        return batch

    # ── StockLedger (append-only) ─────────────────────────────────────────────

    def append_ledger_entry(
        self,
        tenant_id: uuid.UUID,
        product_variant_id: uuid.UUID,
        location_id: uuid.UUID,
        bin_id: uuid.UUID,
        movement_type: MovementType,
        quantity_change: Decimal,
        unit_cost: Decimal,
        batch_id: uuid.UUID | None = None,
        reference_type: str | None = None,
        reference_id: uuid.UUID | None = None,
        notes: str | None = None,
        performed_by_user_id: uuid.UUID | None = None,
    ) -> StockLedger:
        entry = StockLedger(
            tenant_id=tenant_id,
            product_variant_id=product_variant_id,
            location_id=location_id,
            bin_id=bin_id,
            batch_id=batch_id,
            movement_type=str(movement_type),
            quantity_change=quantity_change,
            unit_cost=unit_cost,
            reference_type=reference_type,
            reference_id=reference_id,
            notes=notes,
            performed_by_user_id=performed_by_user_id,
        )
        self.db.add(entry)
        self.db.flush()
        return entry

    def get_ledger_entries(
        self,
        tenant_id: uuid.UUID,
        product_variant_id: uuid.UUID,
        location_id: uuid.UUID,
        limit: int = 100,
    ) -> list[StockLedger]:
        return list(
            self.db.scalars(
                select(StockLedger)
                .where(
                    StockLedger.tenant_id == tenant_id,
                    StockLedger.product_variant_id == product_variant_id,
                    StockLedger.location_id == location_id,
                )
                .order_by(StockLedger.id.desc())
                .limit(limit)
            )
        )

    # ── StockBalance (upsert) ─────────────────────────────────────────────────

    def get_balance(
        self,
        tenant_id: uuid.UUID,
        product_variant_id: uuid.UUID,
        location_id: uuid.UUID,
        bin_id: uuid.UUID,
    ) -> StockBalance | None:
        return self.db.scalar(
            select(StockBalance).where(
                StockBalance.tenant_id == tenant_id,
                StockBalance.product_variant_id == product_variant_id,
                StockBalance.location_id == location_id,
                StockBalance.bin_id == bin_id,
            )
        )

    def upsert_balance(
        self,
        tenant_id: uuid.UUID,
        product_variant_id: uuid.UUID,
        location_id: uuid.UUID,
        bin_id: uuid.UUID,
        quantity_delta: Decimal = Decimal("0"),
        reserved_delta: Decimal = Decimal("0"),
    ) -> StockBalance:
        """
        Atomically adjust the StockBalance for a (variant, location, bin) triple.

        If no balance row exists, one is created with the given deltas as the
        initial values.  This select-then-write pattern avoids SQL MERGE (which
        has driver compatibility issues in some SQLAlchemy sync setups) and is safe inside a
        transaction.
        """
        balance = self.get_balance(tenant_id, product_variant_id, location_id, bin_id)
        if balance is None:
            balance = StockBalance(
                tenant_id=tenant_id,
                product_variant_id=product_variant_id,
                location_id=location_id,
                bin_id=bin_id,
                quantity_on_hand=quantity_delta,
                quantity_reserved=reserved_delta,
            )
            self.db.add(balance)
        else:
            balance.quantity_on_hand += quantity_delta
            balance.quantity_reserved += reserved_delta
        self.db.flush()
        return balance

    def get_stock_summary(
        self,
        tenant_id: uuid.UUID,
        product_variant_id: uuid.UUID,
    ) -> list[StockBalance]:
        """Return all balance rows for a given SKU across all locations/bins."""
        return list(
            self.db.scalars(
                select(StockBalance).where(
                    StockBalance.tenant_id == tenant_id,
                    StockBalance.product_variant_id == product_variant_id,
                )
            )
        )
