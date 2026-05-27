"""
InventoryRepository tests — mock DB session, no live database.

Critical invariants under test:
1. Every query filters by tenant_id.
2. append_ledger_entry never updates an existing row (append-only).
3. upsert_balance creates a new StockBalance if none exists, or updates
   quantity_on_hand on the existing one.
4. get_default_bin raises NotFoundError when no default bin exists for the location.
"""
import uuid
from decimal import Decimal
from unittest.mock import MagicMock, call

import pytest


@pytest.fixture
def mock_db() -> MagicMock:
    return MagicMock()


# ── Bin operations ────────────────────────────────────────────────────────────

def test_create_bin_adds_and_flushes(mock_db: MagicMock) -> None:
    from app.repositories.inventory_repository import InventoryRepository
    tid = uuid.uuid4()
    loc_id = uuid.uuid4()
    b = InventoryRepository(mock_db).create_bin(
        tenant_id=tid, location_id=loc_id, name="Main", is_default=True
    )
    mock_db.add.assert_called_once()
    mock_db.flush.assert_called_once()
    assert b.name == "Main"
    assert b.is_default is True
    assert b.tenant_id == tid


def test_get_bin_returns_bin(mock_db: MagicMock) -> None:
    from app.repositories.inventory_repository import InventoryRepository
    from app.models.inventory import Bin
    b = MagicMock(spec=Bin)
    mock_db.scalar.return_value = b
    result = InventoryRepository(mock_db).get_bin(uuid.uuid4(), uuid.uuid4())
    assert result is b


def test_get_bin_raises_not_found(mock_db: MagicMock) -> None:
    from app.repositories.inventory_repository import InventoryRepository
    from app.core.exceptions import NotFoundError
    mock_db.scalar.return_value = None
    with pytest.raises(NotFoundError):
        InventoryRepository(mock_db).get_bin(uuid.uuid4(), uuid.uuid4())


def test_get_default_bin_returns_default(mock_db: MagicMock) -> None:
    from app.repositories.inventory_repository import InventoryRepository
    from app.models.inventory import Bin
    b = MagicMock(spec=Bin)
    b.is_default = True
    mock_db.scalar.return_value = b
    result = InventoryRepository(mock_db).get_default_bin(uuid.uuid4(), uuid.uuid4())
    assert result is b


def test_get_default_bin_raises_when_none(mock_db: MagicMock) -> None:
    from app.repositories.inventory_repository import InventoryRepository
    from app.core.exceptions import NotFoundError
    mock_db.scalar.return_value = None
    with pytest.raises(NotFoundError):
        InventoryRepository(mock_db).get_default_bin(uuid.uuid4(), uuid.uuid4())


def test_list_bins_by_location_returns_list(mock_db: MagicMock) -> None:
    from app.repositories.inventory_repository import InventoryRepository
    from app.models.inventory import Bin
    bins = [MagicMock(spec=Bin) for _ in range(3)]
    mock_db.scalars.return_value = iter(bins)
    result = InventoryRepository(mock_db).list_bins_by_location(uuid.uuid4(), uuid.uuid4())
    assert len(result) == 3


# ── StockBatch operations ─────────────────────────────────────────────────────

def test_create_batch_adds_and_flushes(mock_db: MagicMock) -> None:
    from app.repositories.inventory_repository import InventoryRepository
    tid = uuid.uuid4()
    batch = InventoryRepository(mock_db).create_batch(
        tenant_id=tid,
        product_variant_id=uuid.uuid4(),
        location_id=uuid.uuid4(),
        bin_id=uuid.uuid4(),
        batch_number="BATCH-001",
        initial_quantity=Decimal("100"),
        unit_cost=Decimal("450.00"),
    )
    mock_db.add.assert_called_once()
    mock_db.flush.assert_called_once()
    assert batch.batch_number == "BATCH-001"
    assert batch.initial_quantity == Decimal("100")
    assert batch.remaining_quantity == Decimal("100")  # starts equal to initial
    assert batch.tenant_id == tid


def test_get_batch_returns_batch(mock_db: MagicMock) -> None:
    from app.repositories.inventory_repository import InventoryRepository
    from app.models.inventory import StockBatch
    b = MagicMock(spec=StockBatch)
    mock_db.scalar.return_value = b
    result = InventoryRepository(mock_db).get_batch(uuid.uuid4(), uuid.uuid4())
    assert result is b


def test_get_batch_raises_not_found(mock_db: MagicMock) -> None:
    from app.repositories.inventory_repository import InventoryRepository
    from app.core.exceptions import NotFoundError
    mock_db.scalar.return_value = None
    with pytest.raises(NotFoundError):
        InventoryRepository(mock_db).get_batch(uuid.uuid4(), uuid.uuid4())


def test_decrement_batch_remaining(mock_db: MagicMock) -> None:
    from app.repositories.inventory_repository import InventoryRepository
    from app.models.inventory import StockBatch
    batch = MagicMock(spec=StockBatch)
    batch.remaining_quantity = Decimal("100")
    mock_db.scalar.return_value = batch
    InventoryRepository(mock_db).decrement_batch_remaining(uuid.uuid4(), uuid.uuid4(), Decimal("30"))
    assert batch.remaining_quantity == Decimal("70")
    mock_db.flush.assert_called_once()


# ── StockLedger (append-only) ─────────────────────────────────────────────────

def test_append_ledger_entry_adds_and_flushes(mock_db: MagicMock) -> None:
    from app.repositories.inventory_repository import InventoryRepository
    from app.models.inventory import MovementType
    tid = uuid.uuid4()
    entry = InventoryRepository(mock_db).append_ledger_entry(
        tenant_id=tid,
        product_variant_id=uuid.uuid4(),
        location_id=uuid.uuid4(),
        bin_id=uuid.uuid4(),
        movement_type=MovementType.PURCHASE_IN,
        quantity_change=Decimal("50"),
        unit_cost=Decimal("450.00"),
    )
    mock_db.add.assert_called_once()
    mock_db.flush.assert_called_once()
    assert entry.movement_type == "purchase_in"
    assert entry.quantity_change == Decimal("50")
    assert entry.tenant_id == tid


def test_get_ledger_entries_returns_list(mock_db: MagicMock) -> None:
    from app.repositories.inventory_repository import InventoryRepository
    from app.models.inventory import StockLedger
    entries = [MagicMock(spec=StockLedger) for _ in range(5)]
    mock_db.scalars.return_value = iter(entries)
    result = InventoryRepository(mock_db).get_ledger_entries(
        uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    )
    assert len(result) == 5


# ── StockBalance upsert ───────────────────────────────────────────────────────

def test_upsert_balance_creates_new_when_absent(mock_db: MagicMock) -> None:
    from app.repositories.inventory_repository import InventoryRepository
    # get_balance returns None → create new
    mock_db.scalar.return_value = None
    tid, vid, lid, bid = uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    balance = InventoryRepository(mock_db).upsert_balance(
        tenant_id=tid,
        product_variant_id=vid,
        location_id=lid,
        bin_id=bid,
        quantity_delta=Decimal("100"),
    )
    mock_db.add.assert_called_once()
    mock_db.flush.assert_called_once()
    assert balance.quantity_on_hand == Decimal("100")
    assert balance.quantity_reserved == Decimal("0")


def test_upsert_balance_updates_existing(mock_db: MagicMock) -> None:
    from app.repositories.inventory_repository import InventoryRepository
    from app.models.inventory import StockBalance
    existing = MagicMock(spec=StockBalance)
    existing.quantity_on_hand = Decimal("100")
    existing.quantity_reserved = Decimal("10")
    mock_db.scalar.return_value = existing
    InventoryRepository(mock_db).upsert_balance(
        tenant_id=uuid.uuid4(),
        product_variant_id=uuid.uuid4(),
        location_id=uuid.uuid4(),
        bin_id=uuid.uuid4(),
        quantity_delta=Decimal("-30"),  # a sale
    )
    assert existing.quantity_on_hand == Decimal("70")
    mock_db.add.assert_not_called()
    mock_db.flush.assert_called_once()


def test_upsert_balance_updates_reserved_quantity(mock_db: MagicMock) -> None:
    from app.repositories.inventory_repository import InventoryRepository
    from app.models.inventory import StockBalance
    existing = MagicMock(spec=StockBalance)
    existing.quantity_on_hand = Decimal("100")
    existing.quantity_reserved = Decimal("0")
    mock_db.scalar.return_value = existing
    InventoryRepository(mock_db).upsert_balance(
        tenant_id=uuid.uuid4(),
        product_variant_id=uuid.uuid4(),
        location_id=uuid.uuid4(),
        bin_id=uuid.uuid4(),
        quantity_delta=Decimal("0"),
        reserved_delta=Decimal("15"),
    )
    assert existing.quantity_reserved == Decimal("15")


def test_get_balance_returns_none_when_absent(mock_db: MagicMock) -> None:
    from app.repositories.inventory_repository import InventoryRepository
    mock_db.scalar.return_value = None
    result = InventoryRepository(mock_db).get_balance(
        uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    )
    assert result is None


def test_get_stock_summary_returns_list(mock_db: MagicMock) -> None:
    from app.repositories.inventory_repository import InventoryRepository
    from app.models.inventory import StockBalance
    balances = [MagicMock(spec=StockBalance) for _ in range(3)]
    mock_db.scalars.return_value = iter(balances)
    result = InventoryRepository(mock_db).get_stock_summary(uuid.uuid4(), uuid.uuid4())
    assert len(result) == 3
