"""Inventory model structure tests — no live DB required."""
import uuid
from decimal import Decimal

import pytest


def test_movement_type_values() -> None:
    from app.models.inventory import MovementType
    assert MovementType.OPENING_STOCK == "opening_stock"
    assert MovementType.PURCHASE_IN == "purchase_in"
    assert MovementType.SALE_OUT == "sale_out"
    assert MovementType.RETURN_IN == "return_in"
    assert MovementType.ADJUSTMENT_IN == "adjustment_in"
    assert MovementType.ADJUSTMENT_OUT == "adjustment_out"
    assert MovementType.TRANSFER_IN == "transfer_in"
    assert MovementType.TRANSFER_OUT == "transfer_out"


def test_movement_type_is_str_enum() -> None:
    from app.models.inventory import MovementType
    from enum import StrEnum
    assert issubclass(MovementType, str)
    # StrEnum values ARE strings — no .value needed
    assert MovementType.PURCHASE_IN == "purchase_in"


def test_bin_has_required_fields() -> None:
    from app.models.inventory import Bin
    b = Bin(
        tenant_id=uuid.uuid4(),
        location_id=uuid.uuid4(),
        name="Shelf A",
        is_default=True,
        is_active=True,
    )
    assert b.name == "Shelf A"
    assert b.is_default is True


def test_bin_table_is_in_inventory_schema() -> None:
    from app.models.inventory import Bin
    assert Bin.__table__.schema == "inventory"


def test_bin_location_id_is_not_null() -> None:
    from app.models.inventory import Bin
    col = Bin.__table__.c["location_id"]
    assert not col.nullable


def test_stock_batch_has_quantities() -> None:
    from app.models.inventory import StockBatch
    sb = StockBatch(
        tenant_id=uuid.uuid4(),
        product_variant_id=uuid.uuid4(),
        location_id=uuid.uuid4(),
        bin_id=uuid.uuid4(),
        batch_number="BATCH-2026-001",
        initial_quantity=Decimal("100"),
        remaining_quantity=Decimal("100"),
        unit_cost=Decimal("450.00"),
    )
    assert sb.initial_quantity == Decimal("100")
    assert sb.remaining_quantity == Decimal("100")


def test_stock_batch_bin_id_is_not_null() -> None:
    """Critical: bin_id must be NOT NULL to prevent phantom-duplicate balances."""
    from app.models.inventory import StockBatch
    col = StockBatch.__table__.c["bin_id"]
    assert not col.nullable


def test_stock_ledger_movement_type_stored_as_string() -> None:
    from app.models.inventory import StockLedger, MovementType
    entry = StockLedger(
        tenant_id=uuid.uuid4(),
        product_variant_id=uuid.uuid4(),
        location_id=uuid.uuid4(),
        bin_id=uuid.uuid4(),
        movement_type=MovementType.PURCHASE_IN,
        quantity_change=Decimal("50"),
        unit_cost=Decimal("450.00"),
    )
    # StrEnum: the value IS the string — no .value needed
    assert entry.movement_type == "purchase_in"


def test_stock_ledger_bin_id_is_not_null() -> None:
    """Critical: bin_id must be NOT NULL on ledger entries."""
    from app.models.inventory import StockLedger
    col = StockLedger.__table__.c["bin_id"]
    assert not col.nullable


def test_stock_ledger_is_in_inventory_schema() -> None:
    from app.models.inventory import StockLedger
    assert StockLedger.__table__.schema == "inventory"


def test_stock_balance_quantity_available() -> None:
    from app.models.inventory import StockBalance
    balance = StockBalance(
        tenant_id=uuid.uuid4(),
        product_variant_id=uuid.uuid4(),
        location_id=uuid.uuid4(),
        bin_id=uuid.uuid4(),
        quantity_on_hand=Decimal("100"),
        quantity_reserved=Decimal("20"),
    )
    assert balance.quantity_available == Decimal("80")


def test_stock_balance_available_is_zero_when_all_reserved() -> None:
    from app.models.inventory import StockBalance
    balance = StockBalance(
        tenant_id=uuid.uuid4(),
        product_variant_id=uuid.uuid4(),
        location_id=uuid.uuid4(),
        bin_id=uuid.uuid4(),
        quantity_on_hand=Decimal("10"),
        quantity_reserved=Decimal("10"),
    )
    assert balance.quantity_available == Decimal("0")


def test_stock_balance_bin_id_is_not_null() -> None:
    """
    Critical design fix: bin_id NOT NULL prevents the phantom-duplicate bug
    from the Supabase design where NULL != NULL in uniqueness checks allowed
    two rows for the same SKU/warehouse to coexist.
    """
    from app.models.inventory import StockBalance
    col = StockBalance.__table__.c["bin_id"]
    assert not col.nullable


def test_stock_balance_composite_unique_constraint_exists() -> None:
    """The four-column composite unique constraint must exist on stock_balances."""
    from app.models.inventory import StockBalance
    constraint_names = {
        c.name for c in StockBalance.__table__.constraints
        if hasattr(c, "name") and c.name
    }
    assert "uq_inventory_balance_variant_location_bin" in constraint_names


def test_stock_balance_quantity_available_not_stored() -> None:
    """quantity_available is a @property, NOT a database column."""
    from app.models.inventory import StockBalance
    col_keys = {c.key for c in StockBalance.__table__.columns}
    assert "quantity_available" not in col_keys
