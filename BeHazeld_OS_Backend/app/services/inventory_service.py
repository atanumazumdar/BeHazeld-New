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
import csv
import io
from decimal import Decimal
from datetime import date
from app.core.pricing import price_with_gst

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, StockNotAvailableError
from app.db.base import Base
from app.models.catalog import ProductVariant
from app.models.inventory import Bin, MovementType, StockBalance, StockBatch, StockLedger
from app.models.tenant import Company, Location
from app.repositories.catalog_repository import CatalogRepository
from app.repositories.inventory_repository import InventoryRepository
from app.schemas.inventory import (
    BulkOpeningStockResponse,
    CreateBinRequest,
    InventoryLocationImportResponse,
    RecordMovementRequest,
)

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
        self.ensure_inventory_tables_available()
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
        self.ensure_inventory_tables_available()
        return self.repo.list_bins_by_location(tenant_id, location_id)

    def ensure_inventory_tables_available(self) -> None:
        """Create inventory schema tables on first-run production databases."""
        bind = self.db.get_bind()
        dialect_name = getattr(getattr(bind, "dialect", None), "name", None)
        if dialect_name != "postgresql":
            return

        with bind.begin() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS inventory"))

        Base.metadata.create_all(
            bind=bind,
            tables=[
                Bin.__table__,
                StockBatch.__table__,
                StockLedger.__table__,
                StockBalance.__table__,
            ],
        )

    def import_locations_bins_csv(
        self,
        tenant_id: uuid.UUID,
        content: bytes,
    ) -> InventoryLocationImportResponse:
        self.ensure_inventory_tables_available()
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = content.decode("latin-1")

        text = self._normalize_csv_text(text)
        dialect = self._detect_csv_dialect(text)
        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
        if reader.fieldnames is None:
            raise ValueError("CSV file is empty or missing a header row")

        headers = {h.strip().lower() for h in reader.fieldnames if h}
        missing = {"location_name"} - headers
        if missing:
            raise ValueError(f"Missing required CSV columns: {', '.join(sorted(missing))}")

        company = self._get_default_company(tenant_id)
        existing_locations = self._location_map(tenant_id)
        created_locations = 0
        created_bins = 0
        skipped = 0
        errors: list[str] = []

        try:
            for line_number, raw_row in enumerate(reader, start=2):
                row = {
                    (key or "").strip().lower(): (value or "").strip()
                    for key, value in raw_row.items()
                }
                location_name = row.get("location_name", "")
                if not location_name:
                    errors.append(f"Line {line_number}: location_name is required")
                    continue

                location_key = location_name.casefold()
                location = existing_locations.get(location_key)
                created_location_this_row = False
                if location is None:
                    location = Location(
                        tenant_id=tenant_id,
                        company_id=company.id,
                        name=location_name,
                        address=row.get("address") or None,
                        is_active=True,
                    )
                    self.db.add(location)
                    self.db.flush()
                    existing_locations[location_key] = location
                    created_locations += 1
                    created_location_this_row = True

                    if not row.get("bin_name"):
                        self.repo.create_bin(tenant_id, location.id, "Main", is_default=True)
                        created_bins += 1

                bin_name = row.get("bin_name", "")
                if not bin_name:
                    if not created_location_this_row:
                        skipped += 1
                    continue

                existing_bins = {
                    bin_obj.name.casefold(): bin_obj
                    for bin_obj in self.repo.list_bins_by_location(tenant_id, location.id)
                }
                bin_key = bin_name.casefold()
                if bin_key in existing_bins:
                    skipped += 1
                    continue

                is_default = self._parse_bool(row.get("is_default", "")) or not existing_bins
                if is_default:
                    self._clear_default_bins(tenant_id, location.id)
                self.repo.create_bin(tenant_id, location.id, bin_name, is_default=is_default)
                created_bins += 1

            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return InventoryLocationImportResponse(
            created_locations=created_locations,
            created_bins=created_bins,
            skipped=skipped,
            errors=errors,
        )

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
        self.ensure_inventory_tables_available()
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
        self.ensure_inventory_tables_available()
        return self.repo.get_ledger_entries(
            tenant_id, product_variant_id, location_id, limit=limit
        )

    def get_stock_summary(
        self, tenant_id: uuid.UUID, product_variant_id: uuid.UUID
    ) -> list[StockBalance]:
        self.ensure_inventory_tables_available()
        return self.repo.get_stock_summary(tenant_id, product_variant_id)

    def list_variants_with_stock_balance(self, tenant_id: uuid.UUID) -> list[uuid.UUID]:
        self.ensure_inventory_tables_available()
        return self.repo.list_variants_with_stock_balance(tenant_id)

    def record_missing_opening_stock(
        self,
        tenant_id: uuid.UUID,
        performed_by_user_id: uuid.UUID | None = None,
    ) -> BulkOpeningStockResponse:
        """Create opening stock of 1 for every active SKU without any balance row."""
        self.ensure_inventory_tables_available()
        try:
            location = self.db.scalar(
                select(Location)
                .where(Location.tenant_id == tenant_id, Location.is_active.is_(True))
                .order_by(Location.name)
            )
            if location is None:
                raise ValueError("No active location found. Please import or create a location first.")

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
                bin_obj = self.repo.create_bin(tenant_id, location.id, "Main", is_default=True)

            stocked_variant_ids = set(self.repo.list_variants_with_stock_balance(tenant_id))
            active_variants = list(
                self.db.scalars(
                    select(ProductVariant)
                    .where(
                        ProductVariant.tenant_id == tenant_id,
                        ProductVariant.status == "active",
                    )
                    .order_by(ProductVariant.sku_code)
                )
            )
            missing_variants = [
                variant for variant in active_variants if variant.id not in stocked_variant_ids
            ]

            quantity = Decimal("1")
            for variant in missing_variants:
                # Catalogue cost is entered before GST; stock valuation uses the
                # actual 5%-GST-inclusive landed cost.
                unit_cost = price_with_gst(variant.cost_price or Decimal("0"), date.today())
                ledger_entry = self.repo.append_ledger_entry(
                    tenant_id=tenant_id,
                    product_variant_id=variant.id,
                    location_id=location.id,
                    bin_id=bin_obj.id,
                    movement_type=MovementType.OPENING_STOCK,
                    quantity_change=quantity,
                    unit_cost=unit_cost,
                    notes="Bulk opening stock: default quantity 1",
                    performed_by_user_id=performed_by_user_id,
                )
                self.repo.create_batch(
                    tenant_id=tenant_id,
                    product_variant_id=variant.id,
                    location_id=location.id,
                    bin_id=bin_obj.id,
                    batch_number=str(ledger_entry.id),
                    initial_quantity=quantity,
                    unit_cost=unit_cost,
                    notes="Bulk opening stock: default quantity 1",
                )
                self.repo.upsert_balance(
                    tenant_id=tenant_id,
                    product_variant_id=variant.id,
                    location_id=location.id,
                    bin_id=bin_obj.id,
                    quantity_delta=quantity,
                )

            self.db.commit()
            return BulkOpeningStockResponse(
                created=len(missing_variants),
                skipped=len(stocked_variant_ids),
                location_id=location.id,
                location_name=location.name,
                bin_id=bin_obj.id,
                bin_name=bin_obj.name,
            )
        except Exception:
            self.db.rollback()
            raise

    def get_balance(
        self,
        tenant_id: uuid.UUID,
        product_variant_id: uuid.UUID,
        location_id: uuid.UUID,
        bin_id: uuid.UUID,
    ) -> StockBalance | None:
        self.ensure_inventory_tables_available()
        return self.repo.get_balance(tenant_id, product_variant_id, location_id, bin_id)

    def _get_default_company(self, tenant_id: uuid.UUID) -> Company:
        company = self.db.scalar(
            select(Company)
            .where(Company.tenant_id == tenant_id, Company.is_active.is_(True))
            .order_by(Company.name)
        )
        if company is None:
            company = Company(
                tenant_id=tenant_id,
                name="Default Company",
                is_active=True,
            )
            self.db.add(company)
            self.db.flush()
        return company

    def _location_map(self, tenant_id: uuid.UUID) -> dict[str, Location]:
        locations = self.db.scalars(
            select(Location)
            .where(Location.tenant_id == tenant_id, Location.is_active.is_(True))
            .order_by(Location.name)
        )
        return {location.name.casefold(): location for location in locations}

    def _clear_default_bins(self, tenant_id: uuid.UUID, location_id: uuid.UUID) -> None:
        for bin_obj in self.repo.list_bins_by_location(tenant_id, location_id):
            bin_obj.is_default = False

    def _parse_bool(self, value: str) -> bool:
        return value.strip().casefold() in {"1", "true", "yes", "y", "default"}

    def _normalize_csv_text(self, text: str) -> str:
        normalized_lines: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith('"') and stripped.endswith('"') and stripped.count('"') == 2:
                normalized_lines.append(stripped[1:-1])
            else:
                normalized_lines.append(line)
        return "\n".join(normalized_lines)

    def _detect_csv_dialect(self, text: str) -> csv.Dialect:
        sample = text[:4096]
        try:
            return csv.Sniffer().sniff(sample, delimiters=",\t;")
        except csv.Error:
            return csv.excel
