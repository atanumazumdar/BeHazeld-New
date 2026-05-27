"""
SalesService unit tests — all DB calls and file I/O mocked.

CRITICAL invariants:
1. "The Golden Sale" — stock deducted → bill created → payment recorded
   → PDF generated → single commit → PDF saved to disk.
2. "Partial Stock Failure" — any line short → StockNotAvailableError raised
   BEFORE any write → no stock deducted, no bill, no payment.
3. "Invalid Variant Rollback" — variant not found → rollback, no writes.
4. "PDF Failure Rollback" — if PDF generation raises → rollback, no stock deducted.
"""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch, call

import pytest

from app.core.exceptions import NotFoundError, StockNotAvailableError
from app.schemas.sales import (
    CreateCustomerRequest,
    CreateSaleBillLineRequest,
    CreateSaleBillRequest,
    CreateSalePaymentRequest,
)
from app.services.sales_service import SalesService


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_service():
    db = MagicMock()
    svc = SalesService(db)
    svc.repo = MagicMock()
    svc.inv_repo = MagicMock()
    svc.catalog_repo = MagicMock()
    return svc, db


def _mock_variant():
    v = MagicMock()
    v.id = uuid.uuid4()
    return v


def _mock_balance(available: Decimal) -> MagicMock:
    b = MagicMock()
    type(b).quantity_available = property(lambda self: available)
    return b


def _mock_bill(invoice_number: str = "INV-000001") -> MagicMock:
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


def _mock_ledger():
    e = MagicMock()
    e.id = uuid.uuid4()
    return e


def _line_req(qty: str = "3", price: str = "500") -> CreateSaleBillLineRequest:
    return CreateSaleBillLineRequest(
        product_variant_id=uuid.uuid4(),
        quantity=Decimal(qty),
        selling_price=Decimal(price),
        tax_rate=Decimal("0.18"),
    )


def _payment_req(amount: str = "1770.00") -> CreateSalePaymentRequest:
    from app.models.sales import SalePaymentMode
    return CreateSalePaymentRequest(
        amount=Decimal(amount),
        payment_mode=SalePaymentMode.CASH,
    )


def _sale_req(
    lines: list[CreateSaleBillLineRequest],
    payment: CreateSalePaymentRequest | None = None,
) -> CreateSaleBillRequest:
    return CreateSaleBillRequest(
        location_id=uuid.uuid4(),
        bin_id=uuid.uuid4(),
        bill_date=date(2026, 5, 25),
        lines=lines,
        payment=payment or _payment_req(),
    )


# ── CRITICAL TEST 1: The Golden Sale ─────────────────────────────────────────

def test_golden_sale_full_chain_verified() -> None:
    """
    THE GOLDEN SALE: 2-item sale
    Verify the complete chain in order:
      Stock deducted (ledger + balance × N) → bill created → payment recorded
      → PDF generated → single db.commit() → PDF saved to disk.
    """
    svc, db = _make_service()
    tenant_id = uuid.uuid4()

    lines = [_line_req("3", "500"), _line_req("2", "800")]
    req = _sale_req(lines)

    svc.catalog_repo.get_variant_by_id = MagicMock(side_effect=[
        _mock_variant(), _mock_variant(),
    ])
    # Ample stock for both lines
    svc.inv_repo.get_balance = MagicMock(
        return_value=_mock_balance(Decimal("100"))
    )
    svc.repo.count_bills_by_tenant = MagicMock(return_value=0)
    svc.repo.get_bill_by_invoice_number = MagicMock(return_value=None)
    bill_mock = _mock_bill("INV-000001")
    svc.repo.create_bill = MagicMock(return_value=bill_mock)
    svc.repo.create_bill_line = MagicMock(return_value=MagicMock())
    svc.inv_repo.append_ledger_entry = MagicMock(return_value=_mock_ledger())
    svc.inv_repo.upsert_balance = MagicMock(return_value=MagicMock())
    svc.repo.create_payment = MagicMock(return_value=MagicMock())

    fake_metadata = MagicMock()
    fake_metadata.invoice_number = "INV-000001"
    fake_metadata.file_path = "/var/invoices/INV-000001.pdf"
    fake_metadata.file_size_bytes = 3000

    with patch("app.services.sales_service.report_service.generate_invoice_pdf") as mock_gen, \
         patch("app.services.sales_service.report_service.save_invoice_pdf") as mock_save:
        mock_gen.return_value = b"%PDF-mock"
        mock_save.return_value = fake_metadata

        bill, metadata = svc.create_sale(tenant_id, req)

    # ── Verify stock deducted for EACH line ──────────────────────────────────
    assert svc.inv_repo.append_ledger_entry.call_count == 2
    assert svc.inv_repo.upsert_balance.call_count == 2

    # Ledger entries must have NEGATIVE quantity_change (SALE_OUT)
    for c in svc.inv_repo.append_ledger_entry.call_args_list:
        assert c.kwargs["quantity_change"] < 0, "SALE_OUT must be negative"

    # Balance upserts must have NEGATIVE delta
    for c in svc.inv_repo.upsert_balance.call_args_list:
        assert c.kwargs["quantity_delta"] < 0, "balance delta must be negative"

    # ── Bill created ─────────────────────────────────────────────────────────
    svc.repo.create_bill.assert_called_once()
    assert svc.repo.create_bill_line.call_count == 2

    # ── Payment recorded ─────────────────────────────────────────────────────
    svc.repo.create_payment.assert_called_once()

    # ── PDF generated ────────────────────────────────────────────────────────
    mock_gen.assert_called_once()

    # ── Single commit ────────────────────────────────────────────────────────
    db.commit.assert_called_once()

    # ── PDF saved to disk ────────────────────────────────────────────────────
    mock_save.assert_called_once()

    assert bill is bill_mock
    assert metadata is fake_metadata


def test_golden_sale_invoice_number_is_sequential() -> None:
    """Invoice number = INV-{count+1:06d}."""
    svc, db = _make_service()
    tenant_id = uuid.uuid4()

    req = _sale_req([_line_req()])
    svc.catalog_repo.get_variant_by_id = MagicMock(return_value=_mock_variant())
    svc.inv_repo.get_balance = MagicMock(return_value=_mock_balance(Decimal("100")))
    svc.repo.count_bills_by_tenant = MagicMock(return_value=41)  # 41 existing → INV-000042
    svc.repo.get_bill_by_invoice_number = MagicMock(return_value=None)
    svc.repo.create_bill = MagicMock(return_value=_mock_bill("INV-000042"))
    svc.repo.create_bill_line = MagicMock(return_value=MagicMock())
    svc.inv_repo.append_ledger_entry = MagicMock(return_value=_mock_ledger())
    svc.inv_repo.upsert_balance = MagicMock(return_value=MagicMock())
    svc.repo.create_payment = MagicMock(return_value=MagicMock())

    with patch("app.services.sales_service.report_service.generate_invoice_pdf",
               return_value=b"%PDF"), \
         patch("app.services.sales_service.report_service.save_invoice_pdf",
               return_value=MagicMock()):
        svc.create_sale(tenant_id, req)

    kwargs = svc.repo.create_bill.call_args.kwargs
    assert kwargs["invoice_number"] == "INV-000042"


# ── CRITICAL TEST 2: Partial Stock Failure ────────────────────────────────────

def test_partial_stock_failure_no_stock_deducted_no_bill() -> None:
    """
    PARTIAL STOCK FAILURE: 3 lines requested, line 2 has only 2 units
    (requested 5). Verify:
      - StockNotAvailableError raised
      - append_ledger_entry NEVER called (no stock deducted)
      - create_bill NEVER called (no bill created)
      - create_payment NEVER called
      - db.rollback() called
      - db.commit() NOT called
    """
    svc, db = _make_service()
    tenant_id = uuid.uuid4()

    lines = [_line_req("3"), _line_req("5"), _line_req("2")]
    req = _sale_req(lines)

    svc.catalog_repo.get_variant_by_id = MagicMock(side_effect=[
        _mock_variant(), _mock_variant(), _mock_variant()
    ])
    # Line 1: OK (100 available), Line 2: SHORT (only 2, need 5), Line 3: not reached
    svc.inv_repo.get_balance = MagicMock(side_effect=[
        _mock_balance(Decimal("100")),   # line 1 — OK
        _mock_balance(Decimal("2")),     # line 2 — INSUFFICIENT (need 5)
    ])

    with pytest.raises(StockNotAvailableError):
        svc.create_sale(tenant_id, req)

    # THE critical assertions
    svc.inv_repo.append_ledger_entry.assert_not_called()
    svc.repo.create_bill.assert_not_called()
    svc.repo.create_payment.assert_not_called()
    db.rollback.assert_called_once()
    db.commit.assert_not_called()


def test_partial_stock_failure_zero_balance_triggers_error() -> None:
    """No balance row (None) → available=0 → raises even for qty=1."""
    svc, db = _make_service()
    tenant_id = uuid.uuid4()

    req = _sale_req([_line_req("1")])
    svc.catalog_repo.get_variant_by_id = MagicMock(return_value=_mock_variant())
    svc.inv_repo.get_balance = MagicMock(return_value=None)  # no stock record

    with pytest.raises(StockNotAvailableError):
        svc.create_sale(tenant_id, req)

    svc.inv_repo.append_ledger_entry.assert_not_called()
    svc.repo.create_bill.assert_not_called()


def test_partial_stock_failure_exact_stock_succeeds() -> None:
    """available == requested quantity → must NOT raise."""
    svc, db = _make_service()
    tenant_id = uuid.uuid4()

    req = _sale_req([_line_req("5")])
    svc.catalog_repo.get_variant_by_id = MagicMock(return_value=_mock_variant())
    svc.inv_repo.get_balance = MagicMock(return_value=_mock_balance(Decimal("5")))  # exactly 5
    svc.repo.count_bills_by_tenant = MagicMock(return_value=0)
    svc.repo.get_bill_by_invoice_number = MagicMock(return_value=None)
    svc.repo.create_bill = MagicMock(return_value=_mock_bill())
    svc.repo.create_bill_line = MagicMock(return_value=MagicMock())
    svc.inv_repo.append_ledger_entry = MagicMock(return_value=_mock_ledger())
    svc.inv_repo.upsert_balance = MagicMock(return_value=MagicMock())
    svc.repo.create_payment = MagicMock(return_value=MagicMock())

    with patch("app.services.sales_service.report_service.generate_invoice_pdf",
               return_value=b"%PDF"), \
         patch("app.services.sales_service.report_service.save_invoice_pdf",
               return_value=MagicMock()):
        svc.create_sale(tenant_id, req)   # must not raise

    db.commit.assert_called_once()


# ── PDF failure triggers rollback ─────────────────────────────────────────────

def test_pdf_generation_failure_rolls_back_entire_transaction() -> None:
    """
    If PDF generation raises (Phase 2c), the exception must propagate
    to the except block, rollback() must fire, and no stock/bill is written.
    PDF failure happens BEFORE any DB write (Phase 3 never starts).
    """
    svc, db = _make_service()
    tenant_id = uuid.uuid4()

    req = _sale_req([_line_req()])
    svc.catalog_repo.get_variant_by_id = MagicMock(return_value=_mock_variant())
    svc.inv_repo.get_balance = MagicMock(return_value=_mock_balance(Decimal("100")))
    svc.repo.count_bills_by_tenant = MagicMock(return_value=0)

    with patch("app.services.sales_service.report_service.generate_invoice_pdf",
               side_effect=RuntimeError("ReportLab font error")):
        with pytest.raises(RuntimeError, match="font error"):
            svc.create_sale(tenant_id, req)

    svc.repo.create_bill.assert_not_called()
    svc.inv_repo.append_ledger_entry.assert_not_called()
    db.rollback.assert_called_once()
    db.commit.assert_not_called()


# ── variant not found ─────────────────────────────────────────────────────────

def test_invalid_variant_rolls_back() -> None:
    svc, db = _make_service()
    tenant_id = uuid.uuid4()

    lines = [_line_req(), _line_req()]
    req = _sale_req(lines)
    svc.catalog_repo.get_variant_by_id = MagicMock(side_effect=[
        _mock_variant(), NotFoundError("Variant missing")
    ])

    with pytest.raises(NotFoundError):
        svc.create_sale(tenant_id, req)

    svc.inv_repo.get_balance.assert_not_called()   # availability check not reached
    svc.repo.create_bill.assert_not_called()
    db.rollback.assert_called_once()


# ── totals calculation ────────────────────────────────────────────────────────

def test_total_amount_computed_correctly_with_discount_and_tax() -> None:
    """
    Line: qty=2, price=500, discount=50, tax=18%
    net_price = 500 - 50 = 450
    line_total = 2 * 450 * 1.18 = 1062.00
    tax = 2 * 450 * 0.18 = 162.00
    discount = 2 * 50 = 100.00
    """
    svc, db = _make_service()
    tenant_id = uuid.uuid4()

    from app.models.sales import SalePaymentMode
    line = CreateSaleBillLineRequest(
        product_variant_id=uuid.uuid4(),
        quantity=Decimal("2"),
        selling_price=Decimal("500"),
        tax_rate=Decimal("0.18"),
        discount_amount=Decimal("50"),
    )
    req = _sale_req([line])
    svc.catalog_repo.get_variant_by_id = MagicMock(return_value=_mock_variant())
    svc.inv_repo.get_balance = MagicMock(return_value=_mock_balance(Decimal("100")))
    svc.repo.count_bills_by_tenant = MagicMock(return_value=0)
    svc.repo.get_bill_by_invoice_number = MagicMock(return_value=None)
    svc.repo.create_bill = MagicMock(return_value=_mock_bill())
    svc.repo.create_bill_line = MagicMock(return_value=MagicMock())
    svc.inv_repo.append_ledger_entry = MagicMock(return_value=_mock_ledger())
    svc.inv_repo.upsert_balance = MagicMock(return_value=MagicMock())
    svc.repo.create_payment = MagicMock(return_value=MagicMock())

    with patch("app.services.sales_service.report_service.generate_invoice_pdf",
               return_value=b"%PDF"), \
         patch("app.services.sales_service.report_service.save_invoice_pdf",
               return_value=MagicMock()):
        svc.create_sale(tenant_id, req)

    bill_kwargs = svc.repo.create_bill.call_args.kwargs
    assert bill_kwargs["total_amount"] == Decimal("1062.00")
    assert bill_kwargs["tax_amount"] == Decimal("162.00")
    assert bill_kwargs["total_discount"] == Decimal("100.00")
