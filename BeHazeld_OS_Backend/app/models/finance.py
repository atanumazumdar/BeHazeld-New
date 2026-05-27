"""
Finance domain models — double-entry accounting.

Entity hierarchy
----------------
ChartOfAccount (hierarchical, self-referential parent_id)
    │
JournalEntry ──► JournalLine ──► ChartOfAccount

Design decisions
----------------
* AccountType uses the standard five-element classification:
    Asset, Liability, Equity, Income, Expense.
  Stored as VARCHAR(20) to avoid SQL Server ENUM limitations.

* ChartOfAccount.account_code is unique per tenant (not globally).
  Standard codes seeded by FinanceService.seed_default_coa():
    1100  Cash and Bank              (Asset)
    1200  Accounts Receivable        (Asset)
    1300  Inventory Asset            (Asset)
    2000  Accounts Payable           (Liability)
    3000  Owner's Equity             (Equity)
    4000  Sales Revenue              (Income)
    4100  Other Income               (Income)
    5000  Cost of Goods Sold (COGS)  (Expense)
    5100  Operating Expenses         (Expense)

* JournalEntry.ref_type identifies the originating business event:
    "sale" | "purchase" | "manual"

* JournalEntry.status: "posted" | "reversed"
  Reversal support is scoped to Phase 5; "reversed" is included in the
  model now so the schema is stable.

* JournalLine: one row per account touched per entry.
  Exactly one of (debit_amount, credit_amount) should be non-zero per line,
  but both columns are stored as non-negative Decimals.
  The balance guard (∑debit = ∑credit) is enforced by FinanceService,
  not by a DB constraint.

* Normal balance convention (for P&L net calculation):
    Asset    — debit increases, credit decreases  → net = debit - credit
    Liability— credit increases, debit decreases  → net = credit - debit
    Equity   — credit increases, debit decreases  → net = credit - debit
    Income   — credit increases, debit decreases  → net = credit - debit
    Expense  — debit increases, credit decreases  → net = debit - credit
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    Date,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

_SCHEMA = "finance"
_AMT    = Numeric(14, 2)


class AccountType(StrEnum):
    ASSET     = "asset"
    LIABILITY = "liability"
    EQUITY    = "equity"
    INCOME    = "income"
    EXPENSE   = "expense"


class JournalRefType(StrEnum):
    SALE     = "sale"
    PURCHASE = "purchase"
    MANUAL   = "manual"


# ── ChartOfAccount ────────────────────────────────────────────────────────────

class ChartOfAccount(Base):
    """
    One node in the tenant's chart of accounts.

    account_code is unique within a tenant.  parent_id supports a two-level
    hierarchy (group → account); deeper nesting is allowed but not required.
    """

    __tablename__ = "chart_of_accounts"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "account_code",
            name="uq_finance_coa_tenant_code",
        ),
        Index("ix_finance_coa_tenant", "tenant_id"),
        {"schema": _SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_SCHEMA}.chart_of_accounts.id", ondelete="SET NULL"),
    )

    account_code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    account_type: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default="1")

    parent: Mapped[ChartOfAccount | None] = relationship(
        "ChartOfAccount", remote_side="ChartOfAccount.id", foreign_keys=[parent_id]
    )
    journal_lines: Mapped[list[JournalLine]] = relationship(back_populates="account")

    def __repr__(self) -> str:
        return f"<ChartOfAccount {self.account_code} {self.name!r}>"


# ── JournalEntry ──────────────────────────────────────────────────────────────

class JournalEntry(Base):
    """
    Header for one balanced double-entry journal posting.

    entry_number is auto-generated (JNL-{seq:08d}).
    Every JournalEntry is balanced: ∑debit_amount == ∑credit_amount across
    all its JournalLines. This is enforced by FinanceService.post_balanced_journal.
    """

    __tablename__ = "journal_entries"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "entry_number",
            name="uq_finance_journal_tenant_number",
        ),
        Index("ix_finance_journal_tenant", "tenant_id"),
        Index("ix_finance_journal_ref", "ref_type", "ref_id"),
        {"schema": _SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.tenants.id", ondelete="CASCADE"),
        nullable=False,
    )

    entry_number: Mapped[str] = mapped_column(String(30), nullable=False)
    entry_date: Mapped[str] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    ref_type: Mapped[str] = mapped_column(String(20), nullable=False)
    ref_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="'posted'"
    )

    lines: Mapped[list[JournalLine]] = relationship(
        back_populates="entry", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<JournalEntry {self.entry_number!r} {self.description!r}>"


# ── JournalLine ───────────────────────────────────────────────────────────────

class JournalLine(Base):
    """
    One account leg of a JournalEntry.

    Exactly one of (debit_amount, credit_amount) should be non-zero per line.
    Both are stored as non-negative values; sign is expressed by which column
    is populated (debit vs credit).
    """

    __tablename__ = "journal_lines"
    __table_args__ = (
        Index("ix_finance_jline_journal", "journal_id"),
        Index("ix_finance_jline_account", "account_id"),
        {"schema": _SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    journal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_SCHEMA}.journal_entries.id", ondelete="CASCADE"),
        nullable=False,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_SCHEMA}.chart_of_accounts.id", ondelete="NO ACTION"),
        nullable=False,
    )

    debit_amount: Mapped[Decimal] = mapped_column(
        _AMT, nullable=False, server_default="0"
    )
    credit_amount: Mapped[Decimal] = mapped_column(
        _AMT, nullable=False, server_default="0"
    )
    memo: Mapped[str | None] = mapped_column(Text)

    entry: Mapped[JournalEntry] = relationship(back_populates="lines")
    account: Mapped[ChartOfAccount] = relationship(back_populates="journal_lines")

    def __repr__(self) -> str:
        return (
            f"<JournalLine account={self.account_id} "
            f"DR={self.debit_amount} CR={self.credit_amount}>"
        )
