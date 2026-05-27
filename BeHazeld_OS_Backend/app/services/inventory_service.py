"""
InventoryService — atomic stock movement engine.

Every call to record_stock_movement() executes inside a single database
transaction:

  1. Validate SKU (variant) exists via CatalogRepository
  2. Validate Bin exists via InventoryRepository
  3. For outward moves: check available balance BEFORE writing anything
  4. Append ledger entry (append-only)
  5. For PURCHASE_IN / OPENING_STOCK: create a StockBatch
  6. Upsert StockBalance (quantity_delta applied, sign already set)
  7. Commit

If any step raises, the except block rolls back and re-raises so the caller
sees the original exception (NotFoundError, StockNotAvailableError, etc.).
No partial state is ever committed.

Sign convention (quantity_change on StockLedger):
  + → inward  (PURCHASE_IN, RETURN_IN, ADJUSTMENT_IN, TRANSFER_IN, OPENING_STOCK)
  - → outward (SALE_OUT, ADJUSTMENT_OUT, TRANSFER_OUT)
"""
import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, StockNotAvailableError
from app.models.inventory import Bin, MovementType, StockBalance, StockBatch, StockLedger
from app.repositories.catalog_repository import CatalogRepository
from app.repositories.inventory_repository import InventoryRepository
from app.schemas.inventory import CreateBinRequest, RecordMovementRequest

# Movement types that remove stock — used to set sign and gate availability check.
_OUTWARD_TYPES: frozenset[MovementType] = frozenset(
    {MovementType.SALE_OUT, MovementType.ADJUSTMENT_OUT, MovementType.TRANSFER_OUT}
)

# Movement types that create a new StockBatch (first inward receipt).
_BATCH_TYPES: frozenset[MovementType] = frozenset(
    {MovementType.PURCHASE_IN, MovementType.OPENING_STOCK}
)


class InventoryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = InventoryRepository(db)
        self.catalog_repo = CatalogRepository(db)

    # ── Bin management ────────────────────────────────────────────────────────

    def create_bin(
        self,
        tenant_id: uuid.UUID,
        location_id: uuid.UUID,
        req: CreateBinRequest,
    ) -> Bin:
        try:
            b = self.repo.create_bin(
                tenant_id=tenant_id,
                location_id=location_id,
                name=req.name,
                is_default=req.is_default,
            )
            self.db.commit()
            self.db.refresh(b)
            return b
        except Exception:
            self.db.rollback()
            raise

    def list_bins(self, tenant_id: uuid.UUID, location_id: uuid.UUID) -> list[Bin]:
        return self.repo.list_bins_by_location(tenant_id, location_id)

    # ── Atomic stock movement ─────────────────────────────────────────────────

    def record_stock_movement(
        self,
        tenant_id: uuid.UUID,
        req: RecordMovementRequest,
        performed_by_user_id: uuid.UUID | None = None,
    ) -> StockLedger:
        """
        Record a stock movement atomically.

        Raises
        ------
        NotFoundError          — variant or bin does not belong to tenant
        StockNotAvailableError — outward move requested more than available stock

        In both error cases the transaction is rolled back and NO ledger entry
        is created.
        """
        try:
            movement_type = MovementType(req.movement_type)
            is_outward = movement_type in _OUTWARD_TYPES

            # ── Step 1: validate variant ──────────────────────────────────────
            # get_variant_by_id raises NotFoundError if missing
            self.catalog_repo.get_variant_by_id(tenant_id, req.product_variant_id)

            # ── Step 2: validate bin ──────────────────────────────────────────
            # get_bin raises NotFoundError if missing
            self.repo.get_bin(tenant_id, req.bin_id)

            # ── Step 3: availability check (outward only) — BEFORE any write ──
            if is_outward:
                balance = self.repo.get_balance(
                    tenant_id,
                    req.product_variant_id,
                    req.location_id,
                    req.bin_id,
                )
                available = (
                    balance.quantity_available
                    if balance is not None
                    else Decimal("0")
                )
                if available < req.quantity:
                    raise StockNotAvailableError(
                        f"Requested {req.quantity} but only {available} available "
                        f"for variant {req.product_variant_id} in bin {req.bin_id}"
                    )

            # ── Step 4: compute signed quantity_change ────────────────────────
            quantity_change = -req.quantity if is_outward else req.quantity

            # ── Step 5: append ledger entry ───────────────────────────────────
            ledger_entry = self.repo.append_ledger_entry(
                tenant_id=tenant_id,
                product_variant_id=req.product_variant_id,
                location_id=req.location_id,
                bin_id=req.bin_id,
                movement_type=movement_type,
                quantity_change=quantity_change,
                unit_cost=req.unit_cost,
                notes=req.notes,
                performed_by_user_id=performed_by_user_id,
            )

            # ── Step 6: create StockBatch for inward receipt events ───────────
            if movement_type in _BATCH_TYPES:
                batch_number = req.batch_number or str(ledger_entry.id)
                self.repo.create_batch(
                    tenant_id=tenant_id,
                    product_variant_id=req.product_variant_id,
                    location_id=req.location_id,
                    bin_id=req.bin_id,
                    batch_number=batch_number,
                    initial_quantity=req.quantity,
                    unit_cost=req.unit_cost,
                )

            # ── Step 7: upsert balance ────────────────────────────────────────
            self.repo.upsert_balance(
                tenant_id=tenant_id,
                product_variant_id=req.product_variant_id,
                location_id=req.location_id,
                bin_id=req.bin_id,
                quantity_delta=quantity_change,
            )

            self.db.commit()
            self.db.refresh(ledger_entry)
            return ledger_entry

        except Exception:
            self.db.rollback()
            raise

    # ── Read helpers ──────────────────────────────────────────────────────────

    def get_ledger(
        self,
        tenant_id: uuid.UUID,
        product_variant_id: uuid.UUID,
        location_id: uuid.UUID,
        limit: int = 100,
    ) -> list[StockLedger]:
        return self.repo.get_ledger_entries(
            tenant_id, product_variant_id, location_id, limit=limit
        )

    def get_stock_summary(
        self, tenant_id: uuid.UUID, product_variant_id: uuid.UUID
    ) -> list[StockBalance]:
        return self.repo.get_stock_summary(tenant_id, product_variant_id)

    def get_balance(
        self,
        tenant_id: uuid.UUID,
        product_variant_id: uuid.UUID,
        location_id: uuid.UUID,
        bin_id: uuid.UUID,
    ) -> StockBalance | None:
        return self.repo.get_balance(tenant_id, product_variant_id, location_id, bin_id)
