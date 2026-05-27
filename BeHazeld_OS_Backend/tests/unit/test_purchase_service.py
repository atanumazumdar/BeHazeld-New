"""
PurchaseService unit tests — all DB calls mocked.

Critical invariants tested:
1. "Purchase Bill Success" — bill created, ledger appended N times,
   batch created N times, balance upserted N times, single commit.
2. "Rollback on Invalid Variant" — if any variant is not found, rollback()
   is called and no bill / ledger / batch / balance is written.
"""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, call

import pytest

from app.core.exceptions import ConflictError, NotFoundError
from app.schemas.purchase import (
    CreatePurchaseBillLineRequest,
    CreatePurchaseBillRequest,
    CreateVendorRequest,
)
from app.services.purchase_service import PurchaseService


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_service():
    db = MagicMock()
    svc = PurchaseService(db)
    svc.repo = MagicMock()
    svc.inv_repo = MagicMock()
    svc.catalog_repo = MagicMock()
    return svc, db


def _mock_variant() -> MagicMock:
    v = MagicMock()
    v.id = uuid.uuid4()
    return v


def _mock_bill(bill_number: str = "INV-001") -> MagicMock:
    b = MagicMock()
    b.id = uuid.uuid4()
    b.bill_number = bill_number
    return b


def _mock_ledger() -> MagicMock:
    e = MagicMock()
    e.id = uuid.uuid4()
    return e


def _line_req(qty: str = "10", cost: str = "200") -> CreatePurchaseBillLineRequest:
    return CreatePurchaseBillLineRequest(
        product_variant_id=uuid.uuid4(),
        quantity=Decimal(qty),
        unit_cost=Decimal(cost),
        tax_rate=Decimal("0.18"),
    )


def _bill_req(lines: list[CreatePurchaseBillLineRequest]) -> CreatePurchaseBillRequest:
    return CreatePurchaseBillRequest(
        vendor_id=uuid.uuid4(),
        location_id=uuid.uuid4(),
        bin_id=uuid.uuid4(),
        bill_number="INV-001",
        bill_date=date(2026, 5, 25),
        lines=lines,
    )


# ── purchase bill success path ────────────────────────────────────────────────

def test_purchase_bill_creates_bill_and_records_stock_for_each_line() -> None:
    """
    CRITICAL: For a 3-line bill, verify:
      - vendor validated
      - all 3 variants validated
      - bill header created once
      - create_bill_line called 3 times
      - append_ledger_entry called 3 times (positive quantity_change)
      - create_batch called 3 times
      - upsert_balance called 3 times
      - single commit
    """
    svc, db = _make_service()
    tenant_id = uuid.uuid4()

    lines = [_line_req("10"), _line_req("5"), _line_req("20")]
    req = _bill_req(lines)

    svc.repo.get_vendor_by_id = MagicMock(return_value=MagicMock())
    svc.catalog_repo.get_variant_by_id = MagicMock(side_effect=[
        _mock_variant(), _mock_variant(), _mock_variant()
    ])
    bill_mock = _mock_bill()
    svc.repo.create_bill = MagicMock(return_value=bill_mock)
    svc.repo.create_bill_line = MagicMock(return_value=MagicMock())
    ledger_mock = _mock_ledger()
    svc.inv_repo.append_ledger_entry = MagicMock(return_value=ledger_mock)
    svc.inv_repo.create_batch = MagicMock(return_value=MagicMock())
    svc.inv_repo.upsert_balance = MagicMock(return_value=MagicMock())
    svc.repo.get_bill_by_number = MagicMock(return_value=None)

    result = svc.create_purchase_bill(tenant_id, req)

    # Bill header created exactly once
    svc.repo.create_bill.assert_called_once()
    # Stock operations called once per line
    assert svc.repo.create_bill_line.call_count == 3
    assert svc.inv_repo.append_ledger_entry.call_count == 3
    assert svc.inv_repo.create_batch.call_count == 3
    assert svc.inv_repo.upsert_balance.call_count == 3
    # Single commit
    db.commit.assert_called_once()
    assert result is bill_mock


def test_purchase_bill_ledger_entries_have_positive_quantity_change() -> None:
    """Stock inward → quantity_change must be positive (not negated)."""
    svc, db = _make_service()
    tenant_id = uuid.uuid4()

    req = _bill_req([_line_req("15")])
    svc.repo.get_vendor_by_id = MagicMock(return_value=MagicMock())
    svc.catalog_repo.get_variant_by_id = MagicMock(return_value=_mock_variant())
    svc.repo.create_bill = MagicMock(return_value=_mock_bill())
    svc.repo.create_bill_line = MagicMock(return_value=MagicMock())
    svc.inv_repo.append_ledger_entry = MagicMock(return_value=_mock_ledger())
    svc.inv_repo.create_batch = MagicMock(return_value=MagicMock())
    svc.inv_repo.upsert_balance = MagicMock(return_value=MagicMock())
    svc.repo.get_bill_by_number = MagicMock(return_value=None)

    svc.create_purchase_bill(tenant_id, req)

    kwargs = svc.inv_repo.append_ledger_entry.call_args.kwargs
    assert kwargs["quantity_change"] == Decimal("15")   # positive


def test_purchase_bill_total_and_tax_computed_correctly() -> None:
    """total_amount = qty * unit_cost * (1 + tax_rate); tax_amount = qty * cost * tax_rate."""
    svc, db = _make_service()
    tenant_id = uuid.uuid4()

    # Line: 10 units @ ₹200, 18% GST
    # line_total = 10 * 200 * 1.18 = 2360.00
    # tax       = 10 * 200 * 0.18 = 360.00
    req = _bill_req([_line_req("10", "200")])  # tax_rate=0.18 from _line_req
    svc.repo.get_vendor_by_id = MagicMock(return_value=MagicMock())
    svc.catalog_repo.get_variant_by_id = MagicMock(return_value=_mock_variant())
    svc.repo.create_bill = MagicMock(return_value=_mock_bill())
    svc.repo.create_bill_line = MagicMock(return_value=MagicMock())
    svc.inv_repo.append_ledger_entry = MagicMock(return_value=_mock_ledger())
    svc.inv_repo.create_batch = MagicMock(return_value=MagicMock())
    svc.inv_repo.upsert_balance = MagicMock(return_value=MagicMock())
    svc.repo.get_bill_by_number = MagicMock(return_value=None)

    svc.create_purchase_bill(tenant_id, req)

    kwargs = svc.repo.create_bill.call_args.kwargs
    assert kwargs["total_amount"] == Decimal("2360.00")
    assert kwargs["tax_amount"] == Decimal("360.00")


def test_purchase_bill_batch_references_bill_number() -> None:
    """StockBatch.purchase_bill_ref must equal the bill_number."""
    svc, db = _make_service()
    tenant_id = uuid.uuid4()

    req = _bill_req([_line_req()])
    svc.repo.get_vendor_by_id = MagicMock(return_value=MagicMock())
    svc.catalog_repo.get_variant_by_id = MagicMock(return_value=_mock_variant())
    svc.repo.create_bill = MagicMock(return_value=_mock_bill("INV-001"))
    svc.repo.create_bill_line = MagicMock(return_value=MagicMock())
    svc.inv_repo.append_ledger_entry = MagicMock(return_value=_mock_ledger())
    svc.inv_repo.create_batch = MagicMock(return_value=MagicMock())
    svc.inv_repo.upsert_balance = MagicMock(return_value=MagicMock())
    svc.repo.get_bill_by_number = MagicMock(return_value=None)

    svc.create_purchase_bill(tenant_id, req)

    batch_kwargs = svc.inv_repo.create_batch.call_args.kwargs
    assert batch_kwargs["purchase_bill_ref"] == "INV-001"


# ── CRITICAL: rollback on invalid variant ────────────────────────────────────

def test_rollback_on_invalid_variant_no_bill_or_stock_written() -> None:
    """
    CRITICAL INVARIANT: If the 2nd variant (of 3) is invalid, NotFoundError
    is raised before any write. create_bill must NOT be called; rollback() IS.

    Simulates the user's "10-item bill with 1 invalid SKU" scenario.
    """
    svc, db = _make_service()
    tenant_id = uuid.uuid4()

    lines = [_line_req("10"), _line_req("5"), _line_req("20")]
    req = _bill_req(lines)

    svc.repo.get_vendor_by_id = MagicMock(return_value=MagicMock())
    # First variant OK, second raises, third never reached
    svc.catalog_repo.get_variant_by_id = MagicMock(side_effect=[
        _mock_variant(),
        NotFoundError("Variant not found"),
        _mock_variant(),
    ])

    with pytest.raises(NotFoundError):
        svc.create_purchase_bill(tenant_id, req)

    # No bill created, no stock written
    svc.repo.create_bill.assert_not_called()
    svc.inv_repo.append_ledger_entry.assert_not_called()
    svc.inv_repo.create_batch.assert_not_called()
    svc.inv_repo.upsert_balance.assert_not_called()
    # Transaction rolled back
    db.rollback.assert_called_once()
    db.commit.assert_not_called()


def test_rollback_on_invalid_vendor() -> None:
    """Vendor not found → rollback, no write at all."""
    svc, db = _make_service()
    tenant_id = uuid.uuid4()

    req = _bill_req([_line_req()])
    svc.repo.get_vendor_by_id = MagicMock(side_effect=NotFoundError("Vendor missing"))

    with pytest.raises(NotFoundError):
        svc.create_purchase_bill(tenant_id, req)

    svc.catalog_repo.get_variant_by_id.assert_not_called()
    svc.repo.create_bill.assert_not_called()
    db.rollback.assert_called_once()


def test_rollback_on_duplicate_bill_number() -> None:
    """Duplicate bill_number → ConflictError → rollback."""
    svc, db = _make_service()
    tenant_id = uuid.uuid4()

    req = _bill_req([_line_req()])
    svc.repo.get_vendor_by_id = MagicMock(return_value=MagicMock())
    svc.catalog_repo.get_variant_by_id = MagicMock(return_value=_mock_variant())
    svc.repo.create_bill = MagicMock(side_effect=ConflictError("Duplicate bill"))

    with pytest.raises(ConflictError):
        svc.create_purchase_bill(tenant_id, req)

    svc.inv_repo.append_ledger_entry.assert_not_called()
    db.rollback.assert_called_once()


# ── payment ───────────────────────────────────────────────────────────────────

def test_record_payment_calls_repo_and_commits() -> None:
    from app.schemas.purchase import RecordVendorPaymentRequest
    from app.models.purchase import PaymentMode

    svc, db = _make_service()
    tenant_id = uuid.uuid4()

    svc.repo.get_bill_by_id = MagicMock(return_value=MagicMock())
    payment_mock = MagicMock()
    svc.repo.create_payment = MagicMock(return_value=payment_mock)

    req = RecordVendorPaymentRequest(
        bill_id=uuid.uuid4(),
        payment_date=date(2026, 5, 25),
        amount=Decimal("1000"),
        payment_mode=PaymentMode.CASH,
    )
    result = svc.record_payment(tenant_id, req)

    svc.repo.create_payment.assert_called_once()
    db.commit.assert_called_once()
    assert result is payment_mock
