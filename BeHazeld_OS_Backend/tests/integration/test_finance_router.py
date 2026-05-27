"""
Finance router integration tests.

Critical scenarios:
1. "Balanced Journal" — POST /finance/journals with ∑DR==∑CR returns 201.
2. "Unbalanced Journal" — POST /finance/journals with ∑DR≠∑CR returns 422
   with error_code=FINANCE_UNBALANCED_ENTRY.
3. Trial balance — GET /finance/reports/trial-balance returns 200 with
   is_balanced flag.
4. P&L — GET /finance/reports/profit-and-loss returns 200 with expected keys.
5. COA seed — POST /finance/accounts/seed returns 201 with created accounts.
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


# ── ORM mock builders ─────────────────────────────────────────────────────────

def _account_orm(code: str = "1100", name: str = "Cash and Bank") -> MagicMock:
    m = MagicMock()
    m.id           = uuid.uuid4()
    m.tenant_id    = _TENANT_ID
    m.parent_id    = None
    m.account_code = code
    m.name         = name
    m.account_type = "asset"
    m.is_active    = True
    return m


def _journal_entry_orm(entry_number: str = "JNL-00000001") -> MagicMock:
    m = MagicMock()
    m.id           = uuid.uuid4()
    m.tenant_id    = _TENANT_ID
    m.entry_number = entry_number
    m.entry_date   = date(2026, 5, 25)
    m.description  = "Test entry"
    m.ref_type     = "manual"
    m.ref_id       = None
    m.status       = "posted"
    m.lines        = []
    return m


def _journal_payload(
    acct_a: str | None = None,
    acct_b: str | None = None,
    dr: str = "1000",
    cr: str = "1000",
) -> dict:
    return {
        "entry_date": "2026-05-25",
        "description": "Test manual journal",
        "ref_type": "manual",
        "lines": [
            {
                "account_id": acct_a or str(uuid.uuid4()),
                "debit_amount": dr,
                "credit_amount": "0",
            },
            {
                "account_id": acct_b or str(uuid.uuid4()),
                "debit_amount": "0",
                "credit_amount": cr,
            },
        ],
    }


# ── COA endpoints ─────────────────────────────────────────────────────────────

def test_list_accounts_returns_200(client: TestClient) -> None:
    with patch("app.api.v1.finance.FinanceService") as MockSvc:
        MockSvc.return_value.list_accounts.return_value = [_account_orm()]
        resp = client.get("/api/v1/finance/accounts")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_create_account_returns_201(client: TestClient) -> None:
    with patch("app.api.v1.finance.FinanceService") as MockSvc:
        MockSvc.return_value.create_account.return_value = _account_orm("9999", "Test Account")
        resp = client.post(
            "/api/v1/finance/accounts",
            json={"account_code": "9999", "name": "Test Account", "account_type": "asset"},
        )
    assert resp.status_code == 201
    assert resp.json()["account_code"] == "9999"


def test_seed_coa_returns_201_with_accounts(client: TestClient) -> None:
    accounts = [_account_orm(str(i), f"Account {i}") for i in range(9)]
    with patch("app.api.v1.finance.FinanceService") as MockSvc:
        MockSvc.return_value.seed_default_coa.return_value = accounts
        resp = client.post("/api/v1/finance/accounts/seed")
    assert resp.status_code == 201
    assert len(resp.json()) == 9


def test_seed_coa_idempotent_returns_empty_list(client: TestClient) -> None:
    """When all accounts already exist, seed returns [] (nothing created)."""
    with patch("app.api.v1.finance.FinanceService") as MockSvc:
        MockSvc.return_value.seed_default_coa.return_value = []
        resp = client.post("/api/v1/finance/accounts/seed")
    assert resp.status_code == 201
    assert resp.json() == []


# ── CRITICAL TEST 1: Balanced Journal ─────────────────────────────────────────

def test_balanced_journal_returns_201(client: TestClient) -> None:
    """
    BALANCED JOURNAL: ∑DR == ∑CR → 201, journal entry returned.
    """
    entry_mock = _journal_entry_orm("JNL-00000001")
    with patch("app.api.v1.finance.FinanceService") as MockSvc:
        MockSvc.return_value.post_manual_journal.return_value = entry_mock
        resp = client.post("/api/v1/finance/journals", json=_journal_payload())

    assert resp.status_code == 201
    body = resp.json()
    assert body["entry_number"] == "JNL-00000001"
    assert body["status"] == "posted"


def test_balanced_journal_response_has_lines(client: TestClient) -> None:
    """Response schema must include `lines` key."""
    entry_mock = _journal_entry_orm()
    with patch("app.api.v1.finance.FinanceService") as MockSvc:
        MockSvc.return_value.post_manual_journal.return_value = entry_mock
        resp = client.post("/api/v1/finance/journals", json=_journal_payload())
    assert "lines" in resp.json()


# ── CRITICAL TEST 2: Unbalanced Journal ──────────────────────────────────────

def test_unbalanced_journal_returns_422(client: TestClient) -> None:
    """
    UNBALANCED JOURNAL: FinanceService raises UnbalancedJournalError →
    router returns 422 with error_code=FINANCE_UNBALANCED_ENTRY.
    """
    from app.core.exceptions import UnbalancedJournalError
    with patch("app.api.v1.finance.FinanceService") as MockSvc:
        MockSvc.return_value.post_manual_journal.side_effect = UnbalancedJournalError(
            "Journal debits (1000) ≠ credits (900)"
        )
        resp = client.post(
            "/api/v1/finance/journals",
            json=_journal_payload(dr="1000", cr="900"),
        )

    assert resp.status_code == 422
    body = resp.json()
    assert body["error_code"] == "FINANCE_UNBALANCED_ENTRY"
    assert body["success"] is False
    assert "correlation_id" in body


def test_unbalanced_journal_error_envelope_is_complete(client: TestClient) -> None:
    """The 422 body must have success, error_code, message, correlation_id."""
    from app.core.exceptions import UnbalancedJournalError
    with patch("app.api.v1.finance.FinanceService") as MockSvc:
        MockSvc.return_value.post_manual_journal.side_effect = UnbalancedJournalError()
        resp = client.post("/api/v1/finance/journals", json=_journal_payload())
    body = resp.json()
    for field in ("success", "error_code", "message", "correlation_id"):
        assert field in body, f"Missing field: {field}"
    assert body["success"] is False


def test_journal_requires_at_least_two_lines(client: TestClient) -> None:
    """Schema validation: journals with only 1 line return 422."""
    payload = {
        "entry_date": "2026-05-25",
        "description": "One line",
        "lines": [
            {"account_id": str(uuid.uuid4()), "debit_amount": "500", "credit_amount": "0"}
        ],
    }
    resp = client.post("/api/v1/finance/journals", json=payload)
    assert resp.status_code == 422


# ── Journal reads ─────────────────────────────────────────────────────────────

def test_list_journals_returns_200(client: TestClient) -> None:
    with patch("app.api.v1.finance.FinanceService") as MockSvc:
        MockSvc.return_value.list_journal_entries.return_value = [
            _journal_entry_orm("JNL-00000001"),
            _journal_entry_orm("JNL-00000002"),
        ]
        resp = client.get("/api/v1/finance/journals")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_get_journal_not_found_returns_404(client: TestClient) -> None:
    from app.core.exceptions import NotFoundError
    entry_id = uuid.uuid4()
    with patch("app.api.v1.finance.FinanceService") as MockSvc:
        MockSvc.return_value.get_journal_entry.side_effect = NotFoundError("Not found")
        resp = client.get(f"/api/v1/finance/journals/{entry_id}")
    assert resp.status_code == 404


# ── CRITICAL TEST 3: Trial Balance ────────────────────────────────────────────

def test_trial_balance_returns_200_with_is_balanced(client: TestClient) -> None:
    """Trial balance endpoint returns 200 with is_balanced bool."""
    from app.schemas.finance import TrialBalanceLine, TrialBalanceResponse
    tb = TrialBalanceResponse(
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
    with patch("app.api.v1.finance.FinanceService") as MockSvc:
        MockSvc.return_value.get_trial_balance.return_value = tb
        resp = client.get("/api/v1/finance/reports/trial-balance")

    assert resp.status_code == 200
    body = resp.json()
    assert body["is_balanced"] is True
    assert "lines" in body
    assert len(body["lines"]) == 2


# ── CRITICAL TEST 4: P&L ──────────────────────────────────────────────────────

def test_profit_and_loss_returns_200_with_all_keys(client: TestClient) -> None:
    """P&L endpoint returns 200 with all required financial fields."""
    from app.schemas.finance import ProfitAndLossReport
    pl = ProfitAndLossReport(
        from_date=None,
        to_date=None,
        total_revenue=Decimal("10000"),
        total_cogs=Decimal("6000"),
        gross_profit=Decimal("10000"),
        total_expenses=Decimal("6000"),
        net_profit=Decimal("4000"),
    )
    with patch("app.api.v1.finance.FinanceService") as MockSvc:
        MockSvc.return_value.get_profit_and_loss.return_value = pl
        resp = client.get("/api/v1/finance/reports/profit-and-loss")

    assert resp.status_code == 200
    body = resp.json()
    for key in ("total_revenue", "total_cogs", "gross_profit", "total_expenses", "net_profit"):
        assert key in body, f"Missing key: {key}"
    assert Decimal(body["net_profit"]) == Decimal("4000")


def test_profit_and_loss_accepts_date_filters(client: TestClient) -> None:
    """P&L endpoint accepts from_date and to_date query params."""
    from app.schemas.finance import ProfitAndLossReport
    pl = ProfitAndLossReport(
        from_date=date(2026, 1, 1),
        to_date=date(2026, 5, 25),
        total_revenue=Decimal("5000"),
        total_cogs=Decimal("3000"),
        gross_profit=Decimal("5000"),
        total_expenses=Decimal("3000"),
        net_profit=Decimal("2000"),
    )
    with patch("app.api.v1.finance.FinanceService") as MockSvc:
        MockSvc.return_value.get_profit_and_loss.return_value = pl
        resp = client.get(
            "/api/v1/finance/reports/profit-and-loss",
            params={"from_date": "2026-01-01", "to_date": "2026-05-25"},
        )
    assert resp.status_code == 200
    MockSvc.return_value.get_profit_and_loss.assert_called_once_with(
        _TENANT_ID,
        date(2026, 1, 1),
        date(2026, 5, 25),
    )
