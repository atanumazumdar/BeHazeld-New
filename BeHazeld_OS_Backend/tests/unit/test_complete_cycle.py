"""
Complete cycle integration tests — verify that SalesService and PurchaseService
call FinanceService within the SAME atomic transaction.

CRITICAL INVARIANTS
───────────────────
1. "The Complete Cycle" (Purchase):
   PurchaseService.create_purchase_bill()
     → stock increases (PURCHASE_IN ledger + balance)
     → _finance_svc.post_purchase_journal() called with correct total_amount
     → single db.commit()

2. "The Revenue Cycle" (Sale):
   SalesService.create_sale()
     → stock decreases (SALE_OUT ledger + balance)
     → _finance_svc.post_sale_journal() called with correct total_amount
     → single db.commit()

3. Finance journal failure → full rollback (no stock or bill written).
"""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import NotFoundError, StockNotAvailableError, UnbalancedJournalError
from app.schemas.purchase import (
    CreatePurchaseBillLineRequest,
    CreatePurchaseBillRequest,
)
from app.schemas.sales import (
    CreateSaleBillLineRequest,
    CreateSaleBillRequest,
    CreateSalePaymentRequest,
)
from app.models.sales import SalePaymentMode
from app.services.purchase_service import PurchaseService
from app.services.sales_service import SalesService


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_purchase_service():
    db = MagicMock()
    svc = PurchaseService(db)
    svc.repo = MagicMock()
    svc.inv_repo = MagicMock()
    svc.catalog_repo = MagicMock()
    svc._finance_svc = MagicMock()
    return svc, db


def _make_sales_service():
    db = MagicMock()
    svc = SalesService(db)
    svc.repo = MagicMock()
    svc.inv_repo = MagicMock()
    svc.catalog_repo = MagicMock()
    svc._finance_svc = MagicMock()
    return svc, db


def _mock_variant() -> MagicMock:
    v = MagicMock()
    v.id = uuid.uuid4()
    return v


def _mock_balance(available: Decimal) -> MagicMock:
    b = MagicMock()
    type(b).quantity_available = property(lambda self: available)
    return b


def _mock_purchase_bill(bill_number: str = "PO-0001") -> MagicMock:
    b = MagicMock()
    b.id = uuid.uuid4()
    b.bill_number = bill_number
    b.total_amount = Decimal("5900.00")
    return b


def _mock_sale_bill(invoice_number: str = "INV-000001") -> MagicMock:
    m = MagicMock()
    m.id = uuid.uuid4()
    m.invoice_number = invoice_number
    m.bill_date = date(2026, 5, 25)
    m.status = "confirmed"
    m.customer = None
    m.lines = []
    m.payments = []
    m.total_amount = Decimal("2360.00")
    m.tax_amount = Decimal("360.00")
    m.total_discount = Decimal("0.00")
    return m


def _purchase_req(
    qty: str = "10", unit_cost: str = "500"
) -> CreatePurchaseBillRequest:
    return CreatePurchaseBillRequest(
        vendor_id=uuid.uuid4(),
        location_id=uuid.uuid4(),
        bin_id=uuid.uuid4(),
        bill_number="PO-0001",
        bill_date=date(2026, 5, 25),
        lines=[
            CreatePurchaseBillLineRequest(
                product_variant_id=uuid.uuid4(),
                quantity=Decimal(qty),
                unit_cost=Decimal(unit_cost),
                tax_rate=Decimal("0.18"),
            )
        ],
    )


def _sale_req() -> CreateSaleBillRequest:
    return CreateSaleBillRequest(
        location_id=uuid.uuid4(),
        bin_id=uuid.uuid4(),
        bill_date=date(2026, 5, 25),
        lines=[
            CreateSaleBillLineRequest(
                product_variant_id=uuid.uuid4(),
                quantity=Decimal("3"),
                selling_price=Decimal("500"),
                tax_rate=Decimal("0.18"),
            )
        ],
        payment=CreateSalePaymentRequest(
            amount=Decimal("1770.00"),
            payment_mode=SalePaymentMode.CASH,
        ),
    )


# ── CRITICAL TEST 1: The Complete Cycle (Purchase) ────────────────────────────

def test_complete_cycle_purchase_calls_finance_journal() -> None:
    """
    THE COMPLETE CYCLE:
    create_purchase_bill() must call _finance_svc.post_purchase_journal()
    with the correct total_amount BEFORE the single db.commit().
    """
    svc, db = _make_purchase_service()
    tenant_id = uuid.uuid4()
    req = _purchase_req(qty="10", unit_cost="500")

    # Expected total: qty=10 × cost=500 × (1+0.18) = 5900.00
    expected_total = Decimal("5900.00")

    svc.repo.get_vendor_by_id = MagicMock(return_value=MagicMock())
    svc.catalog_repo.get_variant_by_id = MagicMock(return_value=_mock_variant())
    bill_mock = _mock_purchase_bill()
    svc.repo.create_bill = MagicMock(return_value=bill_mock)
    svc.repo.create_bill_line = MagicMock(return_value=MagicMock())
    svc.inv_repo.append_ledger_entry = MagicMock(return_value=MagicMock())
    svc.inv_repo.create_batch = MagicMock(return_value=MagicMock())
    svc.inv_repo.upsert_balance = MagicMock(return_value=MagicMock())

    svc.create_purchase_bill(tenant_id, req)

    # Finance journal must be called with the computed total
    svc._finance_svc.post_purchase_journal.assert_called_once()
    kwargs = svc._finance_svc.post_purchase_journal.call_args.kwargs
    assert kwargs["tenant_id"] == tenant_id
    assert kwargs["total_amount"] == expected_total
    assert kwargs["ref_id"] == bill_mock.id
    assert kwargs["entry_date"] == date(2026, 5, 25)


def test_complete_cycle_purchase_single_commit() -> None:
    """Only one db.commit() after both stock and journal writes."""
    svc, db = _make_purchase_service()
    tenant_id = uuid.uuid4()
    req = _purchase_req()

    svc.repo.get_vendor_by_id = MagicMock(return_value=MagicMock())
    svc.catalog_repo.get_variant_by_id = MagicMock(return_value=_mock_variant())
    svc.repo.create_bill = MagicMock(return_value=_mock_purchase_bill())
    svc.repo.create_bill_line = MagicMock(return_value=MagicMock())
    svc.inv_repo.append_ledger_entry = MagicMock(return_value=MagicMock())
    svc.inv_repo.create_batch = MagicMock(return_value=MagicMock())
    svc.inv_repo.upsert_balance = MagicMock(return_value=MagicMock())

    svc.create_purchase_bill(tenant_id, req)

    db.commit.assert_called_once()


def test_complete_cycle_purchase_finance_failure_rolls_back() -> None:
    """
    If _finance_svc.post_purchase_journal() raises, the exception must
    propagate and rollback() must fire — no stock is committed.
    """
    svc, db = _make_purchase_service()
    tenant_id = uuid.uuid4()
    req = _purchase_req()

    svc.repo.get_vendor_by_id = MagicMock(return_value=MagicMock())
    svc.catalog_repo.get_variant_by_id = MagicMock(return_value=_mock_variant())
    svc.repo.create_bill = MagicMock(return_value=_mock_purchase_bill())
    svc.repo.create_bill_line = MagicMock(return_value=MagicMock())
    svc.inv_repo.append_ledger_entry = MagicMock(return_value=MagicMock())
    svc.inv_repo.create_batch = MagicMock(return_value=MagicMock())
    svc.inv_repo.upsert_balance = MagicMock(return_value=MagicMock())
    svc._finance_svc.post_purchase_journal.side_effect = UnbalancedJournalError()

    with pytest.raises(UnbalancedJournalError):
        svc.create_purchase_bill(tenant_id, req)

    db.rollback.assert_called_once()
    db.commit.assert_not_called()


# ── CRITICAL TEST 2: The Revenue Cycle (Sale) ─────────────────────────────────

def test_revenue_cycle_sale_calls_finance_journal() -> None:
    """
    THE REVENUE CYCLE:
    create_sale() must call _finance_svc.post_sale_journal()
    with the correct total_amount BEFORE the single db.commit().
    """
    svc, db = _make_sales_service()
    tenant_id = uuid.uuid4()
    req = _sale_req()

    # Expected total: qty=3 × price=500 × 1.18 = 1770.00
    expected_total = Decimal("1770.00")

    svc.catalog_repo.get_variant_by_id = MagicMock(return_value=_mock_variant())
    svc.inv_repo.get_balance = MagicMock(return_value=_mock_balance(Decimal("100")))
    svc.repo.count_bills_by_tenant = MagicMock(return_value=0)
    svc.repo.get_bill_by_invoice_number = MagicMock(return_value=None)
    bill_mock = _mock_sale_bill()
    bill_mock.total_amount = expected_total
    svc.repo.create_bill = MagicMock(return_value=bill_mock)
    svc.repo.create_bill_line = MagicMock(return_value=MagicMock())
    svc.inv_repo.append_ledger_entry = MagicMock(return_value=MagicMock())
    svc.inv_repo.upsert_balance = MagicMock(return_value=MagicMock())
    svc.repo.create_payment = MagicMock(return_value=MagicMock())

    with patch("app.services.sales_service.report_service.generate_invoice_pdf",
               return_value=b"%PDF"), \
         patch("app.services.sales_service.report_service.save_invoice_pdf",
               return_value=MagicMock()):
        svc.create_sale(tenant_id, req)

    svc._finance_svc.post_sale_journal.assert_called_once()
    kwargs = svc._finance_svc.post_sale_journal.call_args.kwargs
    assert kwargs["tenant_id"] == tenant_id
    assert kwargs["total_amount"] == expected_total
    assert kwargs["ref_id"] == bill_mock.id
    assert kwargs["entry_date"] == date(2026, 5, 25)


def test_revenue_cycle_sale_single_commit() -> None:
    """Only one db.commit() after stock, payment, and journal writes."""
    svc, db = _make_sales_service()
    tenant_id = uuid.uuid4()
    req = _sale_req()

    svc.catalog_repo.get_variant_by_id = MagicMock(return_value=_mock_variant())
    svc.inv_repo.get_balance = MagicMock(return_value=_mock_balance(Decimal("100")))
    svc.repo.count_bills_by_tenant = MagicMock(return_value=0)
    svc.repo.get_bill_by_invoice_number = MagicMock(return_value=None)
    svc.repo.create_bill = MagicMock(return_value=_mock_sale_bill())
    svc.repo.create_bill_line = MagicMock(return_value=MagicMock())
    svc.inv_repo.append_ledger_entry = MagicMock(return_value=MagicMock())
    svc.inv_repo.upsert_balance = MagicMock(return_value=MagicMock())
    svc.repo.create_payment = MagicMock(return_value=MagicMock())

    with patch("app.services.sales_service.report_service.generate_invoice_pdf",
               return_value=b"%PDF"), \
         patch("app.services.sales_service.report_service.save_invoice_pdf",
               return_value=MagicMock()):
        svc.create_sale(tenant_id, req)

    db.commit.assert_called_once()


def test_revenue_cycle_finance_failure_rolls_back_entire_sale() -> None:
    """
    If _finance_svc.post_sale_journal() raises, rollback() fires and
    db.commit() is never called — stock and bill are not persisted.
    """
    svc, db = _make_sales_service()
    tenant_id = uuid.uuid4()
    req = _sale_req()

    svc.catalog_repo.get_variant_by_id = MagicMock(return_value=_mock_variant())
    svc.inv_repo.get_balance = MagicMock(return_value=_mock_balance(Decimal("100")))
    svc.repo.count_bills_by_tenant = MagicMock(return_value=0)
    svc.repo.get_bill_by_invoice_number = MagicMock(return_value=None)
    svc.repo.create_bill = MagicMock(return_value=_mock_sale_bill())
    svc.repo.create_bill_line = MagicMock(return_value=MagicMock())
    svc.inv_repo.append_ledger_entry = MagicMock(return_value=MagicMock())
    svc.inv_repo.upsert_balance = MagicMock(return_value=MagicMock())
    svc.repo.create_payment = MagicMock(return_value=MagicMock())
    svc._finance_svc.post_sale_journal.side_effect = UnbalancedJournalError()

    with pytest.raises(UnbalancedJournalError), \
         patch("app.services.sales_service.report_service.generate_invoice_pdf",
               return_value=b"%PDF"), \
         patch("app.services.sales_service.report_service.save_invoice_pdf",
               return_value=MagicMock()):
        svc.create_sale(tenant_id, req)

    db.rollback.assert_called_once()
    db.commit.assert_not_called()


def test_revenue_cycle_no_finance_svc_still_commits() -> None:
    """
    When _finance_svc is None (default), no journal is posted but
    the sale still succeeds with a single commit.
    """
    db = MagicMock()
    svc = SalesService(db)
    svc.repo = MagicMock()
    svc.inv_repo = MagicMock()
    svc.catalog_repo = MagicMock()
    # _finance_svc left as None (the default)
    tenant_id = uuid.uuid4()
    req = _sale_req()

    svc.catalog_repo.get_variant_by_id = MagicMock(return_value=_mock_variant())
    svc.inv_repo.get_balance = MagicMock(return_value=_mock_balance(Decimal("100")))
    svc.repo.count_bills_by_tenant = MagicMock(return_value=0)
    svc.repo.get_bill_by_invoice_number = MagicMock(return_value=None)
    svc.repo.create_bill = MagicMock(return_value=_mock_sale_bill())
    svc.repo.create_bill_line = MagicMock(return_value=MagicMock())
    svc.inv_repo.append_ledger_entry = MagicMock(return_value=MagicMock())
    svc.inv_repo.upsert_balance = MagicMock(return_value=MagicMock())
    svc.repo.create_payment = MagicMock(return_value=MagicMock())

    with patch("app.services.sales_service.report_service.generate_invoice_pdf",
               return_value=b"%PDF"), \
         patch("app.services.sales_service.report_service.save_invoice_pdf",
               return_value=MagicMock()):
        svc.create_sale(tenant_id, req)

    db.commit.assert_called_once()
