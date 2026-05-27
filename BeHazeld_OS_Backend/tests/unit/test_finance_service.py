"""
FinanceService unit tests — all DB calls mocked.

CRITICAL invariants:
1. Balance Guard — post_balanced_journal raises UnbalancedJournalError when
   ∑DR ≠ ∑CR; succeeds when balanced.
2. Sale Journal — post_sale_journal posts:
     DR Cash (1100)  = total_amount
     CR Revenue (4000) = total_amount
3. Sale Journal with COGS — when cost_amount > 0, also posts:
     DR COGS (5000)      = cost_amount
     CR Inventory (1300) = cost_amount
4. Purchase Journal — post_purchase_journal posts:
     DR Inventory (1300) = total_amount
     CR AP (2000)        = total_amount
5. seed_default_coa — creates 9 accounts; idempotent on second call.
6. Manual journal — post_manual_journal commits on success, rolls back on
   UnbalancedJournalError.
"""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, call, patch

import pytest

from app.core.exceptions import NotFoundError, UnbalancedJournalError
from app.services.finance_service import FinanceService


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_service():
    db = MagicMock()
    svc = FinanceService(db)
    svc.repo = MagicMock()
    return svc, db


def _mock_account(code: str = "1100") -> MagicMock:
    a = MagicMock()
    a.id = uuid.uuid4()
    a.account_code = code
    return a


def _mock_entry() -> MagicMock:
    e = MagicMock()
    e.id = uuid.uuid4()
    e.entry_number = "JNL-00000001"
    return e


# ── CRITICAL TEST 1: Balance Guard ────────────────────────────────────────────

def test_balance_guard_raises_when_debits_exceed_credits() -> None:
    """∑DR > ∑CR must raise UnbalancedJournalError."""
    svc, db = _make_service()
    tenant_id = uuid.uuid4()
    svc.repo.count_journal_entries = MagicMock(return_value=0)

    acct_a = uuid.uuid4()
    acct_b = uuid.uuid4()

    with pytest.raises(UnbalancedJournalError):
        svc.post_balanced_journal(
            tenant_id=tenant_id,
            description="Bad entry",
            ref_type="manual",
            entry_date=date(2026, 5, 25),
            lines=[
                (acct_a, Decimal("500"), Decimal("0")),   # DR 500
                (acct_b, Decimal("0"),   Decimal("400")), # CR 400  ← imbalanced
            ],
        )

    # No entry should be created
    svc.repo.create_journal_entry.assert_not_called()


def test_balance_guard_raises_when_credits_exceed_debits() -> None:
    """∑CR > ∑DR must also raise."""
    svc, db = _make_service()
    tenant_id = uuid.uuid4()
    svc.repo.count_journal_entries = MagicMock(return_value=0)

    with pytest.raises(UnbalancedJournalError):
        svc.post_balanced_journal(
            tenant_id=tenant_id,
            description="Bad entry",
            ref_type="manual",
            entry_date=date(2026, 5, 25),
            lines=[
                (uuid.uuid4(), Decimal("300"), Decimal("0")),
                (uuid.uuid4(), Decimal("0"),   Decimal("500")),
            ],
        )


def test_balance_guard_passes_when_balanced() -> None:
    """∑DR == ∑CR must NOT raise and must create entry + lines."""
    svc, db = _make_service()
    tenant_id = uuid.uuid4()
    acct_a = uuid.uuid4()
    acct_b = uuid.uuid4()

    mock_entry = _mock_entry()
    svc.repo.count_journal_entries = MagicMock(return_value=5)
    svc.repo.create_journal_entry = MagicMock(return_value=mock_entry)
    svc.repo.create_journal_line = MagicMock(return_value=MagicMock())

    entry = svc.post_balanced_journal(
        tenant_id=tenant_id,
        description="Balanced entry",
        ref_type="manual",
        entry_date=date(2026, 5, 25),
        lines=[
            (acct_a, Decimal("1000"), Decimal("0")),
            (acct_b, Decimal("0"),    Decimal("1000")),
        ],
    )

    svc.repo.create_journal_entry.assert_called_once()
    assert svc.repo.create_journal_line.call_count == 2
    assert entry is mock_entry


def test_balance_guard_entry_number_uses_sequence() -> None:
    """Entry number = JNL-{count+1:08d}."""
    svc, db = _make_service()
    tenant_id = uuid.uuid4()
    svc.repo.count_journal_entries = MagicMock(return_value=7)
    mock_entry = _mock_entry()
    svc.repo.create_journal_entry = MagicMock(return_value=mock_entry)
    svc.repo.create_journal_line = MagicMock(return_value=MagicMock())

    svc.post_balanced_journal(
        tenant_id=tenant_id,
        description="Seq test",
        ref_type="manual",
        entry_date=date(2026, 5, 25),
        lines=[
            (uuid.uuid4(), Decimal("100"), Decimal("0")),
            (uuid.uuid4(), Decimal("0"),   Decimal("100")),
        ],
    )

    kwargs = svc.repo.create_journal_entry.call_args.kwargs
    assert kwargs["entry_number"] == "JNL-00000008"


# ── CRITICAL TEST 2: Sale Journal ─────────────────────────────────────────────

def test_post_sale_journal_debit_cash_credit_revenue() -> None:
    """
    Sale journal (no COGS) must post exactly 2 lines:
      DR Cash (1100) = total_amount
      CR Revenue (4000) = total_amount
    """
    svc, db = _make_service()
    tenant_id = uuid.uuid4()
    ref_id    = uuid.uuid4()
    amount    = Decimal("2360.00")

    cash_acct = _mock_account("1100")
    rev_acct  = _mock_account("4000")
    mock_entry = _mock_entry()

    svc.repo.count_journal_entries = MagicMock(return_value=0)
    svc.repo.get_account_by_code = MagicMock(side_effect=[cash_acct, rev_acct])
    svc.repo.create_journal_entry = MagicMock(return_value=mock_entry)
    svc.repo.create_journal_line = MagicMock(return_value=MagicMock())

    svc.post_sale_journal(
        tenant_id=tenant_id,
        ref_id=ref_id,
        entry_date=date(2026, 5, 25),
        total_amount=amount,
    )

    # Exactly 2 lines
    assert svc.repo.create_journal_line.call_count == 2

    calls = svc.repo.create_journal_line.call_args_list
    # Line 1: DR Cash
    line1 = calls[0].kwargs
    assert line1["account_id"] == cash_acct.id
    assert line1["debit_amount"]  == amount
    assert line1["credit_amount"] == Decimal("0")

    # Line 2: CR Revenue
    line2 = calls[1].kwargs
    assert line2["account_id"] == rev_acct.id
    assert line2["debit_amount"]  == Decimal("0")
    assert line2["credit_amount"] == amount


def test_post_sale_journal_with_cogs_posts_four_lines() -> None:
    """
    Sale with cost_amount > 0 must post 4 lines:
      DR Cash, CR Revenue  (revenue cycle)
      DR COGS, CR Inventory (COGS cycle)
    """
    svc, db = _make_service()
    tenant_id = uuid.uuid4()
    amount    = Decimal("2360.00")
    cost      = Decimal("1200.00")

    cash_acct = _mock_account("1100")
    rev_acct  = _mock_account("4000")
    cogs_acct = _mock_account("5000")
    inv_acct  = _mock_account("1300")
    mock_entry = _mock_entry()

    svc.repo.count_journal_entries = MagicMock(return_value=0)
    svc.repo.get_account_by_code = MagicMock(
        side_effect=[cash_acct, rev_acct, cogs_acct, inv_acct]
    )
    svc.repo.create_journal_entry = MagicMock(return_value=mock_entry)
    svc.repo.create_journal_line = MagicMock(return_value=MagicMock())

    svc.post_sale_journal(
        tenant_id=uuid.uuid4(),
        ref_id=uuid.uuid4(),
        entry_date=date(2026, 5, 25),
        total_amount=amount,
        cost_amount=cost,
    )

    assert svc.repo.create_journal_line.call_count == 4
    calls = svc.repo.create_journal_line.call_args_list

    # Line 3: DR COGS
    line3 = calls[2].kwargs
    assert line3["account_id"] == cogs_acct.id
    assert line3["debit_amount"]  == cost
    assert line3["credit_amount"] == Decimal("0")

    # Line 4: CR Inventory
    line4 = calls[3].kwargs
    assert line4["account_id"] == inv_acct.id
    assert line4["debit_amount"]  == Decimal("0")
    assert line4["credit_amount"] == cost


def test_post_sale_journal_zero_cogs_posts_two_lines() -> None:
    """cost_amount=0 (default) must post only 2 lines (no COGS block)."""
    svc, db = _make_service()
    svc.repo.count_journal_entries = MagicMock(return_value=0)
    svc.repo.get_account_by_code = MagicMock(
        side_effect=[_mock_account("1100"), _mock_account("4000")]
    )
    svc.repo.create_journal_entry = MagicMock(return_value=_mock_entry())
    svc.repo.create_journal_line = MagicMock(return_value=MagicMock())

    svc.post_sale_journal(
        tenant_id=uuid.uuid4(),
        ref_id=uuid.uuid4(),
        entry_date=date(2026, 5, 25),
        total_amount=Decimal("500.00"),
        cost_amount=Decimal("0"),
    )
    assert svc.repo.create_journal_line.call_count == 2


# ── CRITICAL TEST 3: Purchase Journal ─────────────────────────────────────────

def test_post_purchase_journal_debit_inventory_credit_ap() -> None:
    """
    Purchase journal must post exactly 2 lines:
      DR Inventory (1300) = total_amount
      CR AP (2000)        = total_amount
    """
    svc, db = _make_service()
    tenant_id = uuid.uuid4()
    amount    = Decimal("5900.00")

    inv_acct = _mock_account("1300")
    ap_acct  = _mock_account("2000")
    mock_entry = _mock_entry()

    svc.repo.count_journal_entries = MagicMock(return_value=0)
    svc.repo.get_account_by_code = MagicMock(side_effect=[inv_acct, ap_acct])
    svc.repo.create_journal_entry = MagicMock(return_value=mock_entry)
    svc.repo.create_journal_line = MagicMock(return_value=MagicMock())

    svc.post_purchase_journal(
        tenant_id=tenant_id,
        ref_id=uuid.uuid4(),
        entry_date=date(2026, 5, 25),
        total_amount=amount,
    )

    assert svc.repo.create_journal_line.call_count == 2

    calls = svc.repo.create_journal_line.call_args_list
    # Line 1: DR Inventory
    line1 = calls[0].kwargs
    assert line1["account_id"] == inv_acct.id
    assert line1["debit_amount"]  == amount
    assert line1["credit_amount"] == Decimal("0")

    # Line 2: CR AP
    line2 = calls[1].kwargs
    assert line2["account_id"] == ap_acct.id
    assert line2["debit_amount"]  == Decimal("0")
    assert line2["credit_amount"] == amount


def test_post_purchase_journal_does_not_commit() -> None:
    """post_purchase_journal must NOT call db.commit (participates in caller's txn)."""
    svc, db = _make_service()
    svc.repo.count_journal_entries = MagicMock(return_value=0)
    svc.repo.get_account_by_code = MagicMock(
        side_effect=[_mock_account("1300"), _mock_account("2000")]
    )
    svc.repo.create_journal_entry = MagicMock(return_value=_mock_entry())
    svc.repo.create_journal_line = MagicMock(return_value=MagicMock())

    svc.post_purchase_journal(
        tenant_id=uuid.uuid4(),
        ref_id=uuid.uuid4(),
        entry_date=date(2026, 5, 25),
        total_amount=Decimal("1000.00"),
    )

    db.commit.assert_not_called()


def test_post_sale_journal_does_not_commit() -> None:
    """post_sale_journal must NOT call db.commit."""
    svc, db = _make_service()
    svc.repo.count_journal_entries = MagicMock(return_value=0)
    svc.repo.get_account_by_code = MagicMock(
        side_effect=[_mock_account("1100"), _mock_account("4000")]
    )
    svc.repo.create_journal_entry = MagicMock(return_value=_mock_entry())
    svc.repo.create_journal_line = MagicMock(return_value=MagicMock())

    svc.post_sale_journal(
        tenant_id=uuid.uuid4(),
        ref_id=uuid.uuid4(),
        entry_date=date(2026, 5, 25),
        total_amount=Decimal("500.00"),
    )

    db.commit.assert_not_called()


# ── CRITICAL TEST 4: seed_default_coa ────────────────────────────────────────

def test_seed_default_coa_creates_nine_accounts() -> None:
    """First seed → 9 accounts created."""
    svc, db = _make_service()
    tenant_id = uuid.uuid4()

    # Every get_account_by_code call raises NotFoundError → account missing
    svc.repo.get_account_by_code = MagicMock(side_effect=NotFoundError("missing"))
    svc.repo.create_account = MagicMock(return_value=_mock_account())

    created = svc.seed_default_coa(tenant_id)

    assert svc.repo.create_account.call_count == 9
    assert len(created) == 9


def test_seed_default_coa_is_idempotent() -> None:
    """Second seed → all accounts exist → nothing created."""
    svc, db = _make_service()
    tenant_id = uuid.uuid4()

    # All accounts already exist
    svc.repo.get_account_by_code = MagicMock(return_value=_mock_account())
    svc.repo.create_account = MagicMock()

    created = svc.seed_default_coa(tenant_id)

    svc.repo.create_account.assert_not_called()
    assert created == []


def test_seed_default_coa_skips_existing_creates_missing() -> None:
    """Partial seed (e.g. 7 exist, 2 missing) → only 2 created."""
    svc, db = _make_service()
    tenant_id = uuid.uuid4()

    call_count = 0
    def side_effect(tenant_id, code):
        nonlocal call_count
        call_count += 1
        if call_count > 7:   # first 7 exist, last 2 raise
            raise NotFoundError("missing")
        return _mock_account(code)

    svc.repo.get_account_by_code = MagicMock(side_effect=side_effect)
    svc.repo.create_account = MagicMock(return_value=_mock_account())

    created = svc.seed_default_coa(tenant_id)
    assert svc.repo.create_account.call_count == 2
    assert len(created) == 2


# ── Manual journal commit/rollback ────────────────────────────────────────────

def test_post_manual_journal_commits_on_success() -> None:
    """post_manual_journal must commit when the entry is balanced."""
    svc, db = _make_service()
    tenant_id = uuid.uuid4()

    svc.repo.count_journal_entries = MagicMock(return_value=0)
    svc.repo.create_journal_entry = MagicMock(return_value=_mock_entry())
    svc.repo.create_journal_line = MagicMock(return_value=MagicMock())

    svc.post_manual_journal(
        tenant_id=tenant_id,
        description="Manual balanced entry",
        entry_date=date(2026, 5, 25),
        lines=[
            (uuid.uuid4(), Decimal("200"), Decimal("0")),
            (uuid.uuid4(), Decimal("0"),   Decimal("200")),
        ],
    )

    db.commit.assert_called_once()
    db.rollback.assert_not_called()


def test_post_manual_journal_rolls_back_on_unbalanced() -> None:
    """post_manual_journal must rollback when journal is unbalanced."""
    svc, db = _make_service()
    tenant_id = uuid.uuid4()
    svc.repo.count_journal_entries = MagicMock(return_value=0)

    with pytest.raises(UnbalancedJournalError):
        svc.post_manual_journal(
            tenant_id=tenant_id,
            description="Broken entry",
            entry_date=date(2026, 5, 25),
            lines=[
                (uuid.uuid4(), Decimal("300"), Decimal("0")),
                (uuid.uuid4(), Decimal("0"),   Decimal("100")),  # CR ≠ DR
            ],
        )

    db.rollback.assert_called_once()
    db.commit.assert_not_called()
