"""
InventoryService unit tests — all DB calls mocked.

Critical invariant (tested explicitly):
  When StockNotAvailableError is raised (insufficient stock),
  append_ledger_entry must NEVER be called — no partial state written.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import MagicMock, call

import pytest

from app.core.exceptions import NotFoundError, StockNotAvailableError
from app.models.inventory import MovementType
from app.schemas.inventory import RecordMovementRequest
from app.services.inventory_service import InventoryService


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_service():
    db = MagicMock()
    svc = InventoryService(db)
    # Pre-stub repos so individual tests only override what they need.
    svc.repo = MagicMock()
    svc.catalog_repo = MagicMock()
    return svc, db


def _inward_req(**overrides) -> RecordMovementRequest:
    defaults = dict(
        product_variant_id=uuid.uuid4(),
        location_id=uuid.uuid4(),
        bin_id=uuid.uuid4(),
        movement_type="purchase_in",
        quantity=Decimal("10"),
        unit_cost=Decimal("200"),
    )
    return RecordMovementRequest(**{**defaults, **overrides})


def _outward_req(**overrides) -> RecordMovementRequest:
    defaults = dict(
        product_variant_id=uuid.uuid4(),
        location_id=uuid.uuid4(),
        bin_id=uuid.uuid4(),
        movement_type="sale_out",
        quantity=Decimal("5"),
        unit_cost=Decimal("0"),
    )
    return RecordMovementRequest(**{**defaults, **overrides})


# ── inward movements ──────────────────────────────────────────────────────────

def test_inward_movement_writes_positive_quantity_change() -> None:
    svc, _ = _make_service()
    req = _inward_req(quantity=Decimal("10"))

    ledger_mock = MagicMock()
    svc.repo.append_ledger_entry = MagicMock(return_value=ledger_mock)
    svc.repo.get_bin = MagicMock(return_value=MagicMock())

    svc.record_stock_movement(uuid.uuid4(), req)

    call_kwargs = svc.repo.append_ledger_entry.call_args.kwargs
    assert call_kwargs["quantity_change"] == Decimal("10")   # positive


def test_inward_movement_creates_stock_batch() -> None:
    """PURCHASE_IN and OPENING_STOCK must create a StockBatch."""
    svc, _ = _make_service()
    req = _inward_req(movement_type="purchase_in", batch_number="BATCH-001")

    ledger_mock = MagicMock()
    svc.repo.append_ledger_entry = MagicMock(return_value=ledger_mock)
    svc.repo.get_bin = MagicMock(return_value=MagicMock())

    svc.record_stock_movement(uuid.uuid4(), req)

    svc.repo.create_batch.assert_called_once()
    call_kwargs = svc.repo.create_batch.call_args.kwargs
    assert call_kwargs["batch_number"] == "BATCH-001"
    assert call_kwargs["initial_quantity"] == Decimal("10")


def test_inward_movement_upserts_balance_with_positive_delta() -> None:
    svc, _ = _make_service()
    req = _inward_req(quantity=Decimal("15"))

    svc.repo.append_ledger_entry = MagicMock(return_value=MagicMock())
    svc.repo.get_bin = MagicMock(return_value=MagicMock())

    svc.record_stock_movement(uuid.uuid4(), req)

    call_kwargs = svc.repo.upsert_balance.call_args.kwargs
    assert call_kwargs["quantity_delta"] == Decimal("15")


def test_return_in_does_not_create_batch() -> None:
    """RETURN_IN is inward but does NOT create a batch."""
    svc, _ = _make_service()
    req = _inward_req(movement_type="return_in")

    svc.repo.append_ledger_entry = MagicMock(return_value=MagicMock())
    svc.repo.get_bin = MagicMock(return_value=MagicMock())

    svc.record_stock_movement(uuid.uuid4(), req)

    svc.repo.create_batch.assert_not_called()


# ── outward movements — the critical path ────────────────────────────────────

def test_outward_movement_writes_negative_quantity_change() -> None:
    svc, _ = _make_service()
    req = _outward_req(quantity=Decimal("5"))

    balance_mock = MagicMock()
    balance_mock.quantity_available = Decimal("100")
    svc.repo.get_balance = MagicMock(return_value=balance_mock)
    svc.repo.append_ledger_entry = MagicMock(return_value=MagicMock())
    svc.repo.get_bin = MagicMock(return_value=MagicMock())

    svc.record_stock_movement(uuid.uuid4(), req)

    call_kwargs = svc.repo.append_ledger_entry.call_args.kwargs
    assert call_kwargs["quantity_change"] == Decimal("-5")   # negative


def test_insufficient_stock_raises_and_no_ledger_entry_written() -> None:
    """
    CRITICAL INVARIANT: When stock is insufficient, StockNotAvailableError is
    raised and append_ledger_entry must NOT be called.  No partial state.
    """
    svc, db = _make_service()
    req = _outward_req(quantity=Decimal("20"))

    balance_mock = MagicMock()
    balance_mock.quantity_available = Decimal("10")   # only 10 available
    svc.repo.get_balance = MagicMock(return_value=balance_mock)
    svc.repo.get_bin = MagicMock(return_value=MagicMock())

    with pytest.raises(StockNotAvailableError):
        svc.record_stock_movement(uuid.uuid4(), req)

    # THE critical assertion: ledger was never touched
    svc.repo.append_ledger_entry.assert_not_called()
    # Transaction was rolled back
    db.rollback.assert_called()


def test_insufficient_stock_zero_balance_raises() -> None:
    """No balance row at all (None) → available=0 → StockNotAvailableError."""
    svc, db = _make_service()
    req = _outward_req(quantity=Decimal("1"))

    svc.repo.get_balance = MagicMock(return_value=None)  # no row exists
    svc.repo.get_bin = MagicMock(return_value=MagicMock())

    with pytest.raises(StockNotAvailableError):
        svc.record_stock_movement(uuid.uuid4(), req)

    svc.repo.append_ledger_entry.assert_not_called()


def test_variant_not_found_raises_and_no_ledger_written() -> None:
    """If the variant doesn't belong to this tenant, no ledger entry is created."""
    svc, db = _make_service()
    req = _inward_req()

    svc.catalog_repo.get_variant_by_id = MagicMock(
        side_effect=NotFoundError("Variant not found")
    )

    with pytest.raises(NotFoundError):
        svc.record_stock_movement(uuid.uuid4(), req)

    svc.repo.append_ledger_entry.assert_not_called()
    db.rollback.assert_called()
