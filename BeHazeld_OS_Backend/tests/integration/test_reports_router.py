"""
Reports router integration tests.

Critical scenarios:
1. "Dashboard Metrics" — GET /dashboard/metrics returns 200 with
   total_revenue, total_cogs, gross_profit, total_tax_collected, active_skus.
2. "Low Stock" — GET /reports/low-stock returns 200 with LowStockItem list.
3. "Trial Balance (report)" — GET /reports/trial-balance returns 200.
4. "GST Report" — GET /reports/gst returns 200 with net_gst_payable.
5. "CSV Export" — GET /exports/trial-balance.csv returns text/csv content-type.
6. "P&L Export" — GET /exports/profit-loss.csv returns text/csv.
"""
import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.deps import TenantContext, get_current_tenant
from app.db.session import get_db
from app.main import app

_TENANT_ID = uuid.uuid4()
_USER_ID   = uuid.uuid4()


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def superuser_ctx() -> TenantContext:
    return TenantContext(
        tenant_id=_TENANT_ID,
        user_id=_USER_ID,
        permissions=["*"],
        is_superuser=True,
    )


@pytest.fixture
def client(superuser_ctx: TenantContext) -> TestClient:
    mock_db = MagicMock()
    app.dependency_overrides[get_db]             = lambda: mock_db
    app.dependency_overrides[get_current_tenant] = lambda: superuser_ctx
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


# ── mock builders ─────────────────────────────────────────────────────────────

def _low_stock_row(sku: str = "SKU-001") -> dict:
    return {
        "variant_id":    uuid.uuid4(),
        "sku_code":      sku,
        "product_id":    uuid.uuid4(),
        "reorder_level": 10,
        "total_on_hand": Decimal("3"),
    }


def _trial_balance():
    from app.schemas.finance import TrialBalanceLine, TrialBalanceResponse
    return TrialBalanceResponse(
        lines=[
            TrialBalanceLine(
                account_code="1100",
                name="Cash and Bank",
                account_type="asset",
                total_debit=Decimal("5000"),
                total_credit=Decimal("2000"),
                net_balance=Decimal("3000"),
            ),
            TrialBalanceLine(
                account_code="4000",
                name="Sales Revenue",
                account_type="income",
                total_debit=Decimal("0"),
                total_credit=Decimal("3000"),
                net_balance=Decimal("3000"),
            ),
        ],
        total_debit=Decimal("5000"),
        total_credit=Decimal("5000"),
        is_balanced=True,
    )


def _pl_report():
    from app.schemas.finance import ProfitAndLossReport
    return ProfitAndLossReport(
        from_date=None,
        to_date=None,
        total_revenue=Decimal("10000"),
        total_cogs=Decimal("6000"),
        gross_profit=Decimal("10000"),
        total_expenses=Decimal("6000"),
        net_profit=Decimal("4000"),
    )


# ── CRITICAL TEST 1: Dashboard Metrics ────────────────────────────────────────

def test_dashboard_metrics_returns_200_with_all_keys(client: TestClient) -> None:
    """
    DASHBOARD METRICS: GET /dashboard/metrics returns 200 with the full
    owner summary — all five keys required.
    """
    with patch("app.api.v1.reports.ReportRepository") as MockRepo:
        instance = MockRepo.return_value
        instance.get_total_revenue.return_value = Decimal("50000")
        instance.get_total_purchase_cost.return_value = Decimal("30000")
        instance.get_gst_summary.return_value = {
            "sales_tax_collected": Decimal("9000"),
            "purchase_tax_paid":   Decimal("5400"),
            "net_gst_payable":     Decimal("3600"),
        }
        instance.count_active_skus.return_value = 42
        resp = client.get("/api/v1/dashboard/metrics")

    assert resp.status_code == 200
    body = resp.json()

    for key in ("total_revenue", "total_cogs", "gross_profit",
                "total_tax_collected", "active_skus"):
        assert key in body, f"Missing key: {key}"

    assert Decimal(body["total_revenue"]) == Decimal("50000")
    assert Decimal(body["total_cogs"])    == Decimal("30000")
    assert Decimal(body["gross_profit"])  == Decimal("20000")
    assert body["active_skus"] == 42


def test_dashboard_metrics_gross_profit_is_revenue_minus_cogs(client: TestClient) -> None:
    """gross_profit must equal total_revenue - total_cogs."""
    with patch("app.api.v1.reports.ReportRepository") as MockRepo:
        instance = MockRepo.return_value
        instance.get_total_revenue.return_value = Decimal("8000")
        instance.get_total_purchase_cost.return_value = Decimal("5000")
        instance.get_gst_summary.return_value = {
            "sales_tax_collected": Decimal("1440"),
            "purchase_tax_paid":   Decimal("900"),
            "net_gst_payable":     Decimal("540"),
        }
        instance.count_active_skus.return_value = 0
        resp = client.get("/api/v1/dashboard/metrics")

    body = resp.json()
    assert Decimal(body["gross_profit"]) == Decimal("8000") - Decimal("5000")


# ── CRITICAL TEST 2: Low Stock ────────────────────────────────────────────────

def test_low_stock_returns_200_with_items(client: TestClient) -> None:
    """
    LOW STOCK: GET /reports/low-stock returns all variants below reorder_level.
    """
    rows = [_low_stock_row("SKU-001"), _low_stock_row("SKU-002")]
    with patch("app.api.v1.reports.ReportRepository") as MockRepo:
        MockRepo.return_value.get_low_stock_variants.return_value = rows
        resp = client.get("/api/v1/reports/low-stock")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert body[0]["sku_code"] == "SKU-001"
    assert Decimal(body[0]["total_on_hand"]) == Decimal("3")
    assert body[0]["reorder_level"] == 10


def test_low_stock_empty_returns_200_empty_list(client: TestClient) -> None:
    with patch("app.api.v1.reports.ReportRepository") as MockRepo:
        MockRepo.return_value.get_low_stock_variants.return_value = []
        resp = client.get("/api/v1/reports/low-stock")
    assert resp.status_code == 200
    assert resp.json() == []


# ── Trial balance (reports router) ────────────────────────────────────────────

def test_trial_balance_report_returns_200(client: TestClient) -> None:
    with patch("app.api.v1.reports.FinanceService") as MockSvc:
        MockSvc.return_value.get_trial_balance.return_value = _trial_balance()
        resp = client.get("/api/v1/reports/trial-balance")

    assert resp.status_code == 200
    body = resp.json()
    assert body["is_balanced"] is True
    assert len(body["lines"]) == 2


# ── CRITICAL TEST 3: GST Report ──────────────────────────────────────────────

def test_gst_report_returns_200_with_net_payable(client: TestClient) -> None:
    """
    GST REPORT: GET /reports/gst returns 200 with:
      sales_tax_collected, purchase_tax_paid, net_gst_payable
    """
    with patch("app.api.v1.reports.ReportRepository") as MockRepo:
        MockRepo.return_value.get_gst_summary.return_value = {
            "sales_tax_collected": Decimal("9000"),
            "purchase_tax_paid":   Decimal("5400"),
            "net_gst_payable":     Decimal("3600"),
        }
        resp = client.get("/api/v1/reports/gst")

    assert resp.status_code == 200
    body = resp.json()
    assert Decimal(body["sales_tax_collected"]) == Decimal("9000")
    assert Decimal(body["purchase_tax_paid"])   == Decimal("5400")
    assert Decimal(body["net_gst_payable"])     == Decimal("3600")


def test_gst_report_accepts_date_filters(client: TestClient) -> None:
    """from_date and to_date query params are forwarded to ReportRepository."""
    with patch("app.api.v1.reports.ReportRepository") as MockRepo:
        MockRepo.return_value.get_gst_summary.return_value = {
            "sales_tax_collected": Decimal("0"),
            "purchase_tax_paid":   Decimal("0"),
            "net_gst_payable":     Decimal("0"),
        }
        resp = client.get(
            "/api/v1/reports/gst",
            params={"from_date": "2026-01-01", "to_date": "2026-05-31"},
        )

    assert resp.status_code == 200
    MockRepo.return_value.get_gst_summary.assert_called_once_with(
        _TENANT_ID,
        date(2026, 1, 1),
        date(2026, 5, 31),
    )


def test_gst_report_net_payable_equals_collected_minus_paid(client: TestClient) -> None:
    """net_gst_payable must equal collected - paid."""
    with patch("app.api.v1.reports.ReportRepository") as MockRepo:
        MockRepo.return_value.get_gst_summary.return_value = {
            "sales_tax_collected": Decimal("12000"),
            "purchase_tax_paid":   Decimal("7200"),
            "net_gst_payable":     Decimal("4800"),
        }
        resp = client.get("/api/v1/reports/gst")

    body = resp.json()
    collected = Decimal(body["sales_tax_collected"])
    paid      = Decimal(body["purchase_tax_paid"])
    net       = Decimal(body["net_gst_payable"])
    assert net == collected - paid


# ── CRITICAL TEST 4: CSV Exports ──────────────────────────────────────────────

def test_trial_balance_csv_export_returns_csv_content_type(client: TestClient) -> None:
    """
    TRIAL BALANCE CSV: GET /exports/trial-balance.csv returns
    Content-Type: text/csv with valid CSV content.
    """
    with patch("app.api.v1.reports.FinanceService") as MockSvc:
        MockSvc.return_value.get_trial_balance.return_value = _trial_balance()
        resp = client.get("/api/v1/exports/trial-balance.csv")

    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    content = resp.text
    assert "Account Code" in content
    assert "Cash and Bank" in content
    assert "Sales Revenue" in content
    assert "BALANCED" in content   # totals row


def test_trial_balance_csv_has_all_required_columns(client: TestClient) -> None:
    """CSV must contain all six header columns."""
    with patch("app.api.v1.reports.FinanceService") as MockSvc:
        MockSvc.return_value.get_trial_balance.return_value = _trial_balance()
        resp = client.get("/api/v1/exports/trial-balance.csv")

    first_line = resp.text.splitlines()[0]
    for col in ("Account Code", "Account Name", "Account Type",
                "Total Debit", "Total Credit", "Net Balance"):
        assert col in first_line, f"Missing column: {col}"


def test_profit_loss_csv_export_returns_csv_content_type(client: TestClient) -> None:
    """
    P&L CSV: GET /exports/profit-loss.csv returns text/csv with P&L rows.
    """
    with patch("app.api.v1.reports.FinanceService") as MockSvc:
        MockSvc.return_value.get_profit_and_loss.return_value = _pl_report()
        resp = client.get("/api/v1/exports/profit-loss.csv")

    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    content = resp.text
    assert "Total Revenue" in content
    assert "Net Profit" in content
    assert "10000" in content


def test_profit_loss_csv_accepts_date_filters(client: TestClient) -> None:
    with patch("app.api.v1.reports.FinanceService") as MockSvc:
        MockSvc.return_value.get_profit_and_loss.return_value = _pl_report()
        resp = client.get(
            "/api/v1/exports/profit-loss.csv",
            params={"from_date": "2026-01-01", "to_date": "2026-05-31"},
        )
    assert resp.status_code == 200
    MockSvc.return_value.get_profit_and_loss.assert_called_once_with(
        _TENANT_ID,
        date(2026, 1, 1),
        date(2026, 5, 31),
    )
