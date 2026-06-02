"""
FinanceRepository — all DB reads/writes for the Finance domain.

Design rules
------------
* Every public method takes tenant_id as its first argument and scopes
  all queries to that tenant (no cross-tenant leaks).
* This repository NEVER commits.  The caller (FinanceService / the owning
  service that embeds a FinanceService call) controls the single commit point.
* Aggregate queries (get_trial_balance, get_balance_by_account_type) use
  SQLAlchemy Core expressions so they remain DB-portable and use the same
  mapped Session.
"""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import NotFoundError
from app.models.finance import AccountType, ChartOfAccount, JournalEntry, JournalLine
from app.schemas.finance import TrialBalanceLine


class FinanceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Chart of Accounts ─────────────────────────────────────────────────────

    def create_account(
        self,
        tenant_id: uuid.UUID,
        account_code: str,
        name: str,
        account_type: str,
        parent_id: uuid.UUID | None = None,
    ) -> ChartOfAccount:
        account = ChartOfAccount(
            tenant_id=tenant_id,
            account_code=account_code,
            name=name,
            account_type=account_type,
            parent_id=parent_id,
        )
        self.db.add(account)
        self.db.flush()
        return account

    def upsert_account_by_code(
        self,
        tenant_id: uuid.UUID,
        account_code: str,
        name: str,
        account_type: str,
        is_active: bool = True,
        parent_id: uuid.UUID | None = None,
    ) -> tuple[ChartOfAccount, bool]:
        stmt = (
            select(ChartOfAccount)
            .where(
                ChartOfAccount.tenant_id == tenant_id,
                ChartOfAccount.account_code == account_code,
            )
        )
        account = self.db.execute(stmt).scalar_one_or_none()
        created = account is None
        if account is None:
            account = ChartOfAccount(
                tenant_id=tenant_id,
                account_code=account_code,
                name=name,
                account_type=account_type,
                parent_id=parent_id,
                is_active=is_active,
            )
            self.db.add(account)
        else:
            account.name = name
            account.account_type = account_type
            account.parent_id = parent_id
            account.is_active = is_active
        self.db.flush()
        return account, created

    def get_account_by_code(
        self, tenant_id: uuid.UUID, account_code: str
    ) -> ChartOfAccount:
        stmt = (
            select(ChartOfAccount)
            .where(
                ChartOfAccount.tenant_id == tenant_id,
                ChartOfAccount.account_code == account_code,
                ChartOfAccount.is_active.is_(True),
            )
        )
        obj = self.db.execute(stmt).scalar_one_or_none()
        if obj is None:
            raise NotFoundError(
                f"Account code '{account_code}' not found for this tenant"
            )
        return obj

    def get_account_by_id(
        self, tenant_id: uuid.UUID, account_id: uuid.UUID
    ) -> ChartOfAccount:
        stmt = (
            select(ChartOfAccount)
            .where(
                ChartOfAccount.id == account_id,
                ChartOfAccount.tenant_id == tenant_id,
            )
        )
        obj = self.db.execute(stmt).scalar_one_or_none()
        if obj is None:
            raise NotFoundError(f"Account {account_id} not found")
        return obj

    def list_accounts(self, tenant_id: uuid.UUID) -> list[ChartOfAccount]:
        stmt = (
            select(ChartOfAccount)
            .where(ChartOfAccount.tenant_id == tenant_id)
            .order_by(ChartOfAccount.account_code)
        )
        return list(self.db.execute(stmt).scalars().all())

    def count_journal_entries(self, tenant_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(JournalEntry)
            .where(JournalEntry.tenant_id == tenant_id)
        )
        return self.db.execute(stmt).scalar_one()

    def get_journal_entry_by_number(
        self,
        tenant_id: uuid.UUID,
        entry_number: str,
    ) -> JournalEntry | None:
        stmt = (
            select(JournalEntry)
            .where(
                JournalEntry.tenant_id == tenant_id,
                JournalEntry.entry_number == entry_number,
            )
        )
        return self.db.execute(stmt).scalar_one_or_none()

    # ── Journal Entries ───────────────────────────────────────────────────────

    def create_journal_entry(
        self,
        tenant_id: uuid.UUID,
        entry_number: str,
        entry_date: date,
        description: str,
        ref_type: str,
        ref_id: uuid.UUID | None = None,
    ) -> JournalEntry:
        entry = JournalEntry(
            tenant_id=tenant_id,
            entry_number=entry_number,
            entry_date=entry_date,
            description=description,
            ref_type=ref_type,
            ref_id=ref_id,
        )
        self.db.add(entry)
        self.db.flush()
        return entry

    def create_journal_line(
        self,
        tenant_id: uuid.UUID,
        journal_id: uuid.UUID,
        account_id: uuid.UUID,
        debit_amount: Decimal = Decimal("0"),
        credit_amount: Decimal = Decimal("0"),
        memo: str | None = None,
    ) -> JournalLine:
        line = JournalLine(
            tenant_id=tenant_id,
            journal_id=journal_id,
            account_id=account_id,
            debit_amount=debit_amount,
            credit_amount=credit_amount,
            memo=memo,
        )
        self.db.add(line)
        self.db.flush()
        return line

    def list_journal_entries(
        self, tenant_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> list[JournalEntry]:
        stmt = (
            select(JournalEntry)
            .options(selectinload(JournalEntry.lines))
            .where(JournalEntry.tenant_id == tenant_id)
            .order_by(JournalEntry.entry_date.desc(), JournalEntry.entry_number.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_journal_entry_by_id(
        self, tenant_id: uuid.UUID, entry_id: uuid.UUID
    ) -> JournalEntry:
        stmt = (
            select(JournalEntry)
            .where(
                JournalEntry.id == entry_id,
                JournalEntry.tenant_id == tenant_id,
            )
        )
        obj = self.db.execute(stmt).scalar_one_or_none()
        if obj is None:
            raise NotFoundError(f"Journal entry {entry_id} not found")
        return obj

    # ── Aggregate Queries ─────────────────────────────────────────────────────

    def get_trial_balance(self, tenant_id: uuid.UUID) -> list[TrialBalanceLine]:
        """
        Return one TrialBalanceLine per account that has at least one journal
        line.  net_balance sign follows normal-balance convention:
            Asset & Expense → debit - credit
            Liability, Equity, Income → credit - debit
        """
        # Aggregate per account
        stmt = (
            select(
                ChartOfAccount.account_code,
                ChartOfAccount.name,
                ChartOfAccount.account_type,
                func.coalesce(func.sum(JournalLine.debit_amount), 0).label("total_debit"),
                func.coalesce(func.sum(JournalLine.credit_amount), 0).label("total_credit"),
            )
            .join(JournalLine, JournalLine.account_id == ChartOfAccount.id)
            .where(ChartOfAccount.tenant_id == tenant_id)
            .group_by(
                ChartOfAccount.account_code,
                ChartOfAccount.name,
                ChartOfAccount.account_type,
            )
            .order_by(ChartOfAccount.account_code)
        )
        rows = self.db.execute(stmt).all()

        result: list[TrialBalanceLine] = []
        for row in rows:
            dr = Decimal(str(row.total_debit))
            cr = Decimal(str(row.total_credit))
            # Net balance by normal-balance convention
            if row.account_type in (AccountType.ASSET, AccountType.EXPENSE):
                net = dr - cr
            else:
                net = cr - dr
            result.append(
                TrialBalanceLine(
                    account_code=row.account_code,
                    name=row.name,
                    account_type=row.account_type,
                    total_debit=dr,
                    total_credit=cr,
                    net_balance=net,
                )
            )
        return result

    def get_balance_by_account_type(
        self,
        tenant_id: uuid.UUID,
        account_type: str,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> Decimal:
        """
        Return the net balance for all accounts of a given type, optionally
        filtered by journal entry_date range.

        Net balance sign:
            Asset & Expense  → SUM(debit) - SUM(credit)
            Liability/Equity/Income → SUM(credit) - SUM(debit)
        """
        stmt = (
            select(
                func.coalesce(func.sum(JournalLine.debit_amount), 0).label("dr"),
                func.coalesce(func.sum(JournalLine.credit_amount), 0).label("cr"),
            )
            .join(JournalEntry, JournalLine.journal_id == JournalEntry.id)
            .join(ChartOfAccount, JournalLine.account_id == ChartOfAccount.id)
            .where(
                ChartOfAccount.tenant_id == tenant_id,
                ChartOfAccount.account_type == account_type,
            )
        )
        if from_date is not None:
            stmt = stmt.where(JournalEntry.entry_date >= from_date)
        if to_date is not None:
            stmt = stmt.where(JournalEntry.entry_date <= to_date)

        row = self.db.execute(stmt).one()
        dr = Decimal(str(row.dr))
        cr = Decimal(str(row.cr))

        if account_type in (AccountType.ASSET, AccountType.EXPENSE):
            return dr - cr
        return cr - dr
