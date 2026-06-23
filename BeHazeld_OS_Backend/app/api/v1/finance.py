"""
Finance router — chart of accounts, journal entries, trial balance, P&L.

Permission matrix
-----------------
GET  /accounts                         : finance.accounts.view
POST /accounts                         : finance.accounts.create
POST /accounts/seed                    : finance.accounts.seed
GET  /journals                         : finance.journals.view
GET  /journals/{id}                    : finance.journals.view
POST /journals                         : finance.journals.create
POST /journals/{id}/reverse            : finance.journals.create
GET  /reports/trial-balance            : finance.reports.view
GET  /reports/profit-and-loss          : finance.reports.view
"""
import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import TenantContext, get_current_tenant, require_permission
from app.core.exceptions import ValidationError
from app.db.session import get_db
from app.schemas.finance import (
    AccountResponse,
    CreateAccountRequest,
    CreateJournalEntryRequest,
    FinanceImportResponse,
    JournalEntryResponse,
    ProfitAndLossReport,
    TrialBalanceResponse,
)
from app.services.finance_service import FinanceService

router = APIRouter(prefix="/finance", tags=["finance"])


# ── Chart of Accounts ─────────────────────────────────────────────────────────

@router.get("/accounts", response_model=list[AccountResponse])
def list_accounts(
    ctx: TenantContext = Depends(require_permission("finance.accounts.view")),
    db: Session = Depends(get_db),
) -> list[AccountResponse]:
    return FinanceService(db).list_accounts(ctx.tenant_id)  # type: ignore[return-value]


@router.post(
    "/accounts",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_account(
    body: CreateAccountRequest,
    ctx: TenantContext = Depends(require_permission("finance.accounts.create")),
    db: Session = Depends(get_db),
) -> AccountResponse:
    return FinanceService(db).create_account(  # type: ignore[return-value]
        tenant_id=ctx.tenant_id,
        account_code=body.account_code,
        name=body.name,
        account_type=body.account_type,
        parent_id=body.parent_id,
    )


@router.post(
    "/accounts/seed",
    response_model=list[AccountResponse],
    status_code=status.HTTP_201_CREATED,
)
def seed_default_coa(
    ctx: TenantContext = Depends(require_permission("finance.accounts.seed")),
    db: Session = Depends(get_db),
) -> list[AccountResponse]:
    """
    Seed the 9 standard chart-of-accounts entries for this tenant.
    Idempotent: accounts that already exist are skipped.
    """
    svc = FinanceService(db)
    created = svc.seed_default_coa(ctx.tenant_id)
    db.commit()
    return created  # type: ignore[return-value]


@router.post(
    "/accounts/import",
    response_model=FinanceImportResponse,
)
async def import_account_codes(
    file: UploadFile = File(...),
    ctx: TenantContext = Depends(require_permission("finance.accounts.create")),
    db: Session = Depends(get_db),
) -> FinanceImportResponse:
    if not _is_csv_upload(file):
        raise ValidationError("Uploaded file must be a CSV")
    try:
        return FinanceService(db).import_account_codes_csv(ctx.tenant_id, await file.read())
    except ValueError as exc:
        db.rollback()
        raise ValidationError(str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise ValidationError(f"Account code import failed: {exc}") from exc


# ── Journal Entries ───────────────────────────────────────────────────────────

@router.get("/journals", response_model=list[JournalEntryResponse])
def list_journal_entries(
    skip: int = 0,
    limit: int = 50,
    ctx: TenantContext = Depends(require_permission("finance.journals.view")),
    db: Session = Depends(get_db),
) -> list[JournalEntryResponse]:
    return FinanceService(db).list_journal_entries(ctx.tenant_id, skip=skip, limit=limit)  # type: ignore[return-value]


@router.post(
    "/journals/import",
    response_model=FinanceImportResponse,
)
async def import_journal_entries(
    file: UploadFile = File(...),
    ctx: TenantContext = Depends(require_permission("finance.journals.create")),
    db: Session = Depends(get_db),
) -> FinanceImportResponse:
    if not _is_csv_upload(file):
        raise ValidationError("Uploaded file must be a CSV")
    try:
        return FinanceService(db).import_journal_entries_csv(ctx.tenant_id, await file.read())
    except ValueError as exc:
        db.rollback()
        raise ValidationError(str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise ValidationError(f"Journal entry import failed: {exc}") from exc


@router.get("/journals/{entry_id}", response_model=JournalEntryResponse)
def get_journal_entry(
    entry_id: uuid.UUID,
    ctx: TenantContext = Depends(require_permission("finance.journals.view")),
    db: Session = Depends(get_db),
) -> JournalEntryResponse:
    return FinanceService(db).get_journal_entry(ctx.tenant_id, entry_id)  # type: ignore[return-value]


@router.post(
    "/journals",
    response_model=JournalEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_manual_journal(
    body: CreateJournalEntryRequest,
    ctx: TenantContext = Depends(require_permission("finance.journals.create")),
    db: Session = Depends(get_db),
) -> JournalEntryResponse:
    """
    Post a manually crafted balanced journal entry.
    Returns 422 if ∑debits ≠ ∑credits.
    """
    svc = FinanceService(db)
    lines = [
        (ln.account_id, ln.debit_amount, ln.credit_amount)
        for ln in body.lines
    ]
    return svc.post_manual_journal(  # type: ignore[return-value]
        tenant_id=ctx.tenant_id,
        description=body.description,
        entry_date=body.entry_date,
        lines=lines,
        ref_id=body.ref_id,
    )


@router.post(
    "/journals/{entry_id}/reverse",
    response_model=JournalEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
def reverse_journal_entry(
    entry_id: uuid.UUID,
    ctx: TenantContext = Depends(require_permission("finance.journals.create")),
    db: Session = Depends(get_db),
) -> JournalEntryResponse:
    """
    Create an equal-and-opposite journal entry and mark the original reversed.
    """
    return FinanceService(db).reverse_journal_entry(ctx.tenant_id, entry_id)  # type: ignore[return-value]


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/reports/trial-balance", response_model=TrialBalanceResponse)
def get_trial_balance(
    ctx: TenantContext = Depends(require_permission("finance.reports.view")),
    db: Session = Depends(get_db),
) -> TrialBalanceResponse:
    return FinanceService(db).get_trial_balance(ctx.tenant_id)


@router.get("/reports/profit-and-loss", response_model=ProfitAndLossReport)
def get_profit_and_loss(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    ctx: TenantContext = Depends(require_permission("finance.reports.view")),
    db: Session = Depends(get_db),
) -> ProfitAndLossReport:
    return FinanceService(db).get_profit_and_loss(ctx.tenant_id, from_date, to_date)


def _is_csv_upload(file: UploadFile) -> bool:
    is_csv_filename = bool(file.filename and file.filename.lower().endswith(".csv"))
    is_csv_content = file.content_type in {"text/csv", "application/csv", "application/vnd.ms-excel"}
    return is_csv_filename or is_csv_content
