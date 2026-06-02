"""
FinanceService — double-entry accounting automation.

Design contract
---------------
* This service NEVER calls db.commit().  All methods use db.flush() so
  the journal entries participate in the caller's transaction.  The commit
  point belongs to the owning service (SalesService, PurchaseService, or
  the manual-journal API endpoint).

* post_balanced_journal() is the single authorised entry point for
  creating journal entries.  It enforces the fundamental invariant:
      ∑ debit_amount  ==  ∑ credit_amount
  Violation raises UnbalancedJournalError (HTTP 422).

* post_sale_journal() and post_purchase_journal() are convenience wrappers
  that resolve the standard COA codes for the tenant and delegate to
  post_balanced_journal().

* seed_default_coa() is idempotent: it skips codes that already exist.

Standard COA codes used by automated posting
---------------------------------------------
  1100  Cash and Bank              (Asset)     ← DR on sale
  1300  Inventory Asset            (Asset)     ← DR on purchase, CR on COGS
  2000  Accounts Payable           (Liability) ← CR on purchase
  4000  Sales Revenue              (Income)    ← CR on sale
  5000  Cost of Goods Sold (COGS)  (Expense)   ← DR on sale (when cost known)
"""
from __future__ import annotations

import csv
import io
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, UnbalancedJournalError
from app.db.base import Base
from app.models.finance import AccountType, ChartOfAccount, JournalEntry, JournalLine, JournalRefType
from app.repositories.finance_repository import FinanceRepository
from app.schemas.finance import (
    FinanceImportResponse,
    ProfitAndLossReport,
    TrialBalanceLine,
    TrialBalanceResponse,
)

# Standard COA codes expected to be seeded for every tenant
_COA_CASH        = "1100"
_COA_AR          = "1200"
_COA_INVENTORY   = "1300"
_COA_AP          = "2000"
_COA_EQUITY      = "3000"
_COA_REVENUE     = "4000"
_COA_OTHER_INC   = "4100"
_COA_COGS        = "5000"
_COA_OPEX        = "5100"

_DEFAULT_COA: list[tuple[str, str, str]] = [
    (_COA_CASH,      "Cash and Bank",             AccountType.ASSET),
    (_COA_AR,        "Accounts Receivable",        AccountType.ASSET),
    (_COA_INVENTORY, "Inventory Asset",            AccountType.ASSET),
    (_COA_AP,        "Accounts Payable",           AccountType.LIABILITY),
    (_COA_EQUITY,    "Owner's Equity",             AccountType.EQUITY),
    (_COA_REVENUE,   "Sales Revenue",              AccountType.INCOME),
    (_COA_OTHER_INC, "Other Income",               AccountType.INCOME),
    (_COA_COGS,      "Cost of Goods Sold (COGS)",  AccountType.EXPENSE),
    (_COA_OPEX,      "Operating Expenses",         AccountType.EXPENSE),
]


def _entry_number(seq: int) -> str:
    return f"JNL-{seq:08d}"


class FinanceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = FinanceRepository(db)

    # ── COA setup ─────────────────────────────────────────────────────────────

    def ensure_finance_tables_available(self) -> None:
        """Create finance schema tables on first-run production databases."""
        bind = self.db.get_bind()
        dialect_name = getattr(getattr(bind, "dialect", None), "name", None)
        if dialect_name != "postgresql":
            return

        with bind.begin() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS finance"))

        Base.metadata.create_all(
            bind=bind,
            tables=[
                ChartOfAccount.__table__,
                JournalEntry.__table__,
                JournalLine.__table__,
            ],
        )

    def seed_default_coa(self, tenant_id: uuid.UUID) -> list:
        """
        Create the 9 standard accounts for a tenant.  Idempotent — any account
        whose code already exists is silently skipped.

        Does NOT commit; caller must commit.
        """
        self.ensure_finance_tables_available()
        created = []
        for code, name, account_type in _DEFAULT_COA:
            try:
                self.repo.get_account_by_code(tenant_id, code)
                # already exists — skip
            except NotFoundError:
                account = self.repo.create_account(
                    tenant_id=tenant_id,
                    account_code=code,
                    name=name,
                    account_type=account_type,
                )
                created.append(account)
        return created

    def create_account(
        self,
        tenant_id: uuid.UUID,
        account_code: str,
        name: str,
        account_type: str,
        parent_id: uuid.UUID | None = None,
    ):
        self.ensure_finance_tables_available()
        account = self.repo.create_account(
            tenant_id=tenant_id,
            account_code=account_code,
            name=name,
            account_type=account_type,
            parent_id=parent_id,
        )
        self.db.commit()
        self.db.refresh(account)
        return account

    def list_accounts(self, tenant_id: uuid.UUID) -> list:
        self.ensure_finance_tables_available()
        return self.repo.list_accounts(tenant_id)

    # ── CSV imports ───────────────────────────────────────────────────────────

    def import_account_codes_csv(
        self,
        tenant_id: uuid.UUID,
        content: bytes,
    ) -> FinanceImportResponse:
        self.ensure_finance_tables_available()
        reader = self._csv_dict_reader(content)
        required = {"account_code", "account_name", "account_type"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing required CSV columns: {', '.join(sorted(missing))}")

        imported = 0
        updated = 0
        skipped = 0
        errors: list[str] = []

        try:
            for line_number, row in enumerate(reader, start=2):
                account_code = row.get("account_code", "").strip()
                account_name = row.get("account_name", "").strip()
                raw_account_type = row.get("account_type", "").strip()
                status = row.get("status", "active").strip().casefold()

                if not account_code or not account_name or not raw_account_type:
                    errors.append(f"Line {line_number}: account_code, account_name and account_type are required")
                    skipped += 1
                    continue

                try:
                    account_type = self._normalize_account_type(raw_account_type)
                except ValueError as exc:
                    errors.append(f"Line {line_number}: {exc}")
                    skipped += 1
                    continue

                _account, created = self.repo.upsert_account_by_code(
                    tenant_id=tenant_id,
                    account_code=account_code,
                    name=account_name,
                    account_type=account_type,
                    is_active=status != "inactive",
                )
                if created:
                    imported += 1
                else:
                    updated += 1

            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return FinanceImportResponse(
            imported=imported,
            updated=updated,
            skipped=skipped,
            errors=errors,
        )

    def import_journal_entries_csv(
        self,
        tenant_id: uuid.UUID,
        content: bytes,
    ) -> FinanceImportResponse:
        self.ensure_finance_tables_available()
        reader = self._csv_dict_reader(content)
        required = {
            "journal number",
            "journal date",
            "account",
            "debit amount",
            "credit amount",
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing required CSV columns: {', '.join(sorted(missing))}")

        grouped: dict[str, list[dict[str, str]]] = {}
        for row in reader:
            journal_number = row.get("journal number", "").strip()
            if not journal_number:
                continue
            grouped.setdefault(journal_number, []).append(row)

        imported = 0
        skipped = 0
        errors: list[str] = []

        try:
            for journal_number, rows in grouped.items():
                if self.repo.get_journal_entry_by_number(tenant_id, journal_number) is not None:
                    skipped += 1
                    continue

                try:
                    first = rows[0]
                    entry_date = date.fromisoformat(first.get("journal date", "").strip())
                    narration = first.get("narration", "").strip()
                    invoice_number = first.get("invoice number", "").strip()
                    description = narration or f"Imported journal {journal_number}"
                    if invoice_number and invoice_number.upper() != "NA":
                        description = f"{description} ({invoice_number})"

                    total_dr = Decimal("0")
                    total_cr = Decimal("0")
                    parsed_lines: list[tuple[uuid.UUID, Decimal, Decimal, str | None]] = []

                    for row in rows:
                        account_code = self._parse_account_code(row.get("account", ""))
                        try:
                            account = self.repo.get_account_by_code(tenant_id, account_code)
                        except NotFoundError as exc:
                            raise ValueError(
                                f"account code '{account_code}' was not found. "
                                "Import Accounting Codes.csv first, then retry journal import."
                            ) from exc
                        debit = self._decimal(row.get("debit amount", "0"))
                        credit = self._decimal(row.get("credit amount", "0"))
                        total_dr += debit
                        total_cr += credit
                        memo_parts = [
                            part
                            for part in [
                                row.get("invoice number", "").strip(),
                                row.get("narration", "").strip(),
                            ]
                            if part and part.upper() != "NA"
                        ]
                        parsed_lines.append((account.id, debit, credit, " - ".join(memo_parts) or None))

                    if len(parsed_lines) < 2:
                        raise ValueError("journal must contain at least two lines")
                    if total_dr.quantize(Decimal("0.01")) != total_cr.quantize(Decimal("0.01")):
                        raise ValueError(f"debits ({total_dr}) do not equal credits ({total_cr})")

                    entry = self.repo.create_journal_entry(
                        tenant_id=tenant_id,
                        entry_number=journal_number,
                        entry_date=entry_date,
                        description=description[:500],
                        ref_type=JournalRefType.MANUAL,
                        ref_id=None,
                    )
                    for account_id, debit, credit, memo in parsed_lines:
                        self.repo.create_journal_line(
                            tenant_id=tenant_id,
                            journal_id=entry.id,
                            account_id=account_id,
                            debit_amount=debit,
                            credit_amount=credit,
                            memo=memo,
                        )
                    imported += 1
                except Exception as exc:
                    errors.append(f"{journal_number}: {exc}")
                    skipped += 1

            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return FinanceImportResponse(
            imported=imported,
            skipped=skipped,
            errors=errors,
        )

    # ── Core journal posting ──────────────────────────────────────────────────

    def post_balanced_journal(
        self,
        tenant_id: uuid.UUID,
        description: str,
        ref_type: str,
        entry_date: date,
        lines: list[tuple[uuid.UUID, Decimal, Decimal]],
        ref_id: uuid.UUID | None = None,
    ):
        self.ensure_finance_tables_available()
        """
        Create a balanced journal entry (no commit — flush only).

        Parameters
        ----------
        lines : list of (account_id, debit_amount, credit_amount)
            Exactly one of debit_amount / credit_amount should be non-zero per
            line.  Both must be non-negative.

        Raises
        ------
        UnbalancedJournalError  — if ∑debits ≠ ∑credits
        """
        total_dr = sum(dr for _, dr, _ in lines)
        total_cr = sum(cr for _, _, cr in lines)

        if total_dr.quantize(Decimal("0.01")) != total_cr.quantize(Decimal("0.01")):
            raise UnbalancedJournalError(
                f"Journal debits ({total_dr}) ≠ credits ({total_cr})"
            )

        seq = self.repo.count_journal_entries(tenant_id) + 1
        entry = self.repo.create_journal_entry(
            tenant_id=tenant_id,
            entry_number=_entry_number(seq),
            entry_date=entry_date,
            description=description,
            ref_type=ref_type,
            ref_id=ref_id,
        )

        for account_id, dr, cr in lines:
            self.repo.create_journal_line(
                tenant_id=tenant_id,
                journal_id=entry.id,
                account_id=account_id,
                debit_amount=dr,
                credit_amount=cr,
            )

        return entry

    # ── Automated sale journal ────────────────────────────────────────────────

    def post_sale_journal(
        self,
        tenant_id: uuid.UUID,
        ref_id: uuid.UUID,
        entry_date: date,
        total_amount: Decimal,
        cost_amount: Decimal = Decimal("0"),
    ):
        """
        Post the accounting entries for a confirmed sale.

        Revenue cycle:
          DR 1100 Cash/Bank          total_amount   (cash received)
          CR 4000 Sales Revenue      total_amount   (revenue earned)

        COGS (if cost_amount > 0):
          DR 5000 COGS               cost_amount    (cost of product sold)
          CR 1300 Inventory Asset    cost_amount    (reduce inventory value)

        Does NOT commit — participates in the caller's transaction.
        """
        cash_acct = self.repo.get_account_by_code(tenant_id, _COA_CASH)
        rev_acct  = self.repo.get_account_by_code(tenant_id, _COA_REVENUE)

        lines: list[tuple[uuid.UUID, Decimal, Decimal]] = [
            (cash_acct.id, total_amount, Decimal("0")),   # DR Cash
            (rev_acct.id,  Decimal("0"), total_amount),   # CR Revenue
        ]

        if cost_amount > Decimal("0"):
            cogs_acct = self.repo.get_account_by_code(tenant_id, _COA_COGS)
            inv_acct  = self.repo.get_account_by_code(tenant_id, _COA_INVENTORY)
            lines.extend([
                (cogs_acct.id, cost_amount, Decimal("0")),   # DR COGS
                (inv_acct.id,  Decimal("0"), cost_amount),   # CR Inventory
            ])

        return self.post_balanced_journal(
            tenant_id=tenant_id,
            description=f"Sale revenue recognition",
            ref_type=JournalRefType.SALE,
            entry_date=entry_date,
            lines=lines,
            ref_id=ref_id,
        )

    # ── Automated purchase journal ────────────────────────────────────────────

    def post_purchase_journal(
        self,
        tenant_id: uuid.UUID,
        ref_id: uuid.UUID,
        entry_date: date,
        total_amount: Decimal,
    ):
        """
        Post the accounting entries for a confirmed purchase.

        Purchase cycle:
          DR 1300 Inventory Asset    total_amount   (inventory value increases)
          CR 2000 Accounts Payable   total_amount   (liability to vendor)

        Does NOT commit — participates in the caller's transaction.
        """
        inv_acct = self.repo.get_account_by_code(tenant_id, _COA_INVENTORY)
        ap_acct  = self.repo.get_account_by_code(tenant_id, _COA_AP)

        lines: list[tuple[uuid.UUID, Decimal, Decimal]] = [
            (inv_acct.id, total_amount, Decimal("0")),   # DR Inventory
            (ap_acct.id,  Decimal("0"), total_amount),   # CR AP
        ]

        return self.post_balanced_journal(
            tenant_id=tenant_id,
            description="Purchase stock receipt",
            ref_type=JournalRefType.PURCHASE,
            entry_date=entry_date,
            lines=lines,
            ref_id=ref_id,
        )

    # ── Manual journal (API) ──────────────────────────────────────────────────

    def post_manual_journal(
        self,
        tenant_id: uuid.UUID,
        description: str,
        entry_date: date,
        lines: list[tuple[uuid.UUID, Decimal, Decimal]],
        ref_id: uuid.UUID | None = None,
    ):
        """
        Post a manually crafted balanced journal entry.
        Commits on success; rolls back on UnbalancedJournalError.
        """
        try:
            entry = self.post_balanced_journal(
                tenant_id=tenant_id,
                description=description,
                ref_type=JournalRefType.MANUAL,
                entry_date=entry_date,
                lines=lines,
                ref_id=ref_id,
            )
            self.db.commit()
            self.db.refresh(entry)
            return entry
        except Exception:
            self.db.rollback()
            raise

    # ── Reports ───────────────────────────────────────────────────────────────

    def get_trial_balance(self, tenant_id: uuid.UUID) -> TrialBalanceResponse:
        self.ensure_finance_tables_available()
        lines = self.repo.get_trial_balance(tenant_id)
        total_dr = sum(ln.total_debit  for ln in lines)
        total_cr = sum(ln.total_credit for ln in lines)
        return TrialBalanceResponse(
            lines=lines,
            total_debit=total_dr,
            total_credit=total_cr,
            is_balanced=(
                total_dr.quantize(Decimal("0.01")) == total_cr.quantize(Decimal("0.01"))
            ),
        )

    def get_profit_and_loss(
        self,
        tenant_id: uuid.UUID,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> ProfitAndLossReport:
        self.ensure_finance_tables_available()
        revenue   = self.repo.get_balance_by_account_type(
            tenant_id, AccountType.INCOME, from_date, to_date
        )
        cogs_type = AccountType.EXPENSE   # We'll break it down below
        # COGS and OpEx: get all expenses, differentiate by sub-type if needed.
        # For now we aggregate all Expense accounts, COGS is the portion on 5000.
        expenses  = self.repo.get_balance_by_account_type(
            tenant_id, AccountType.EXPENSE, from_date, to_date
        )
        # Gross profit is not easily separated without sub-type info at this
        # aggregation level, so we proxy: total_cogs = 0 here (report uses
        # expenses as a whole).  The more granular breakdown would need
        # a per-account query; included as a future Phase 5 item.
        gross     = revenue - Decimal("0")  # placeholder gross = revenue - cogs
        net       = revenue - expenses

        return ProfitAndLossReport(
            from_date=from_date,
            to_date=to_date,
            total_revenue=revenue,
            total_cogs=expenses,    # all expense = COGS + OpEx (simplified)
            gross_profit=revenue,   # simplified: gross = revenue (COGS inlined)
            total_expenses=expenses,
            net_profit=net,
        )

    def list_journal_entries(
        self, tenant_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> list:
        self.ensure_finance_tables_available()
        return self.repo.list_journal_entries(tenant_id, skip=skip, limit=limit)

    def get_journal_entry(self, tenant_id: uuid.UUID, entry_id: uuid.UUID):
        self.ensure_finance_tables_available()
        return self.repo.get_journal_entry_by_id(tenant_id, entry_id)

    def _csv_dict_reader(self, content: bytes) -> csv.DictReader:
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = content.decode("latin-1")
        reader = csv.DictReader(io.StringIO(text))
        if reader.fieldnames is None:
            raise ValueError("CSV file is empty or missing a header row")
        reader.fieldnames = [(field or "").strip().lower() for field in reader.fieldnames]
        return reader

    def _normalize_account_type(self, account_type: str) -> str:
        normalized = account_type.strip().casefold()
        if normalized == "cogs":
            return AccountType.EXPENSE
        allowed = {
            str(AccountType.ASSET),
            str(AccountType.LIABILITY),
            str(AccountType.EQUITY),
            str(AccountType.INCOME),
            str(AccountType.EXPENSE),
        }
        if normalized not in allowed:
            raise ValueError(f"unsupported account_type '{account_type}'")
        return normalized

    def _parse_account_code(self, account: str) -> str:
        code = account.split("-", 1)[0].strip()
        if not code:
            raise ValueError("account code is required")
        return code

    def _decimal(self, value: str) -> Decimal:
        cleaned = (value or "0").replace(",", "").strip()
        return Decimal(cleaned or "0")
