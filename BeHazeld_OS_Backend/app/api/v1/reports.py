"""
Reports router — owner's business intelligence dashboard.

All endpoints require authentication (finance.reports.view permission).
All aggregate queries are executed via ReportRepository using SQLAlchemy
SUM/COUNT aggregations — no Python-side row accumulation.

Endpoints
---------
GET /dashboard/metrics          — revenue, COGS, gross profit, active SKUs
GET /reports/low-stock          — variants below reorder threshold
GET /reports/trial-balance      — full financial snapshot (from FinanceService)
GET /reports/gst                — GST collected vs paid for a date range
GET /exports/trial-balance.csv  — trial balance as CSV download
GET /exports/profit-loss.csv    — P&L as CSV download
"""
import csv
import io
import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import TenantContext, require_permission
from app.db.session import get_db
from app.repositories.report_repository import ReportRepository
from app.schemas.finance import TrialBalanceResponse
from app.schemas.reports import DashboardMetrics, GstSummary, LowStockItem
from app.services.finance_service import FinanceService

router = APIRouter(tags=["reports"])


# ── Dashboard metrics ─────────────────────────────────────────────────────────

@router.get("/dashboard/metrics", response_model=DashboardMetrics)
def get_dashboard_metrics(
    ctx: TenantContext = Depends(require_permission("finance.reports.view")),
    db: Session = Depends(get_db),
) -> DashboardMetrics:
    """
    Return the top-level business summary for the owner dashboard.

    All numbers are computed via SQL aggregations (no full table scans in Python).
    COGS is approximated as total confirmed purchase cost (Phase 5 will track
    actual unit costs via FIFO batch allocation).
    """
    repo = ReportRepository(db)

    pl = FinanceService(db).get_profit_and_loss(ctx.tenant_id)
    gst_data = repo.get_gst_summary(ctx.tenant_id)
    skus     = repo.count_active_skus(ctx.tenant_id)

    return DashboardMetrics(
        total_revenue=pl.total_revenue,
        total_cogs=pl.total_cogs,
        gross_profit=pl.gross_profit,
        total_tax_collected=gst_data["sales_tax_collected"],
        active_skus=skus,
    )


# ── Low stock ─────────────────────────────────────────────────────────────────

@router.get("/reports/low-stock", response_model=list[LowStockItem])
def get_low_stock_report(
    ctx: TenantContext = Depends(require_permission("finance.reports.view")),
    db: Session = Depends(get_db),
) -> list[LowStockItem]:
    """
    List all active SKUs where total on-hand stock across all locations
    is at or below their reorder_level threshold.
    """
    rows = ReportRepository(db).get_low_stock_variants(ctx.tenant_id)
    return [LowStockItem(**row) for row in rows]


# ── Trial balance ─────────────────────────────────────────────────────────────

@router.get("/reports/trial-balance", response_model=TrialBalanceResponse)
def get_trial_balance(
    ctx: TenantContext = Depends(require_permission("finance.reports.view")),
    db: Session = Depends(get_db),
) -> TrialBalanceResponse:
    """Full trial balance — one row per account with DR/CR totals and net balance."""
    return FinanceService(db).get_trial_balance(ctx.tenant_id)


# ── GST report ────────────────────────────────────────────────────────────────

@router.get("/reports/gst", response_model=GstSummary)
def get_gst_report(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    ctx: TenantContext = Depends(require_permission("finance.reports.view")),
    db: Session = Depends(get_db),
) -> GstSummary:
    """
    GST summary for a date range.

    Returns:
    - sales_tax_collected  — outward tax (GST Output)
    - purchase_tax_paid    — inward tax / Input Tax Credit (ITC)
    - net_gst_payable      — payable to government = collected - ITC
    """
    data = ReportRepository(db).get_gst_summary(ctx.tenant_id, from_date, to_date)
    return GstSummary(
        from_date=from_date,
        to_date=to_date,
        **data,
    )


# ── CSV exports ───────────────────────────────────────────────────────────────

@router.get("/exports/trial-balance.csv")
def export_trial_balance_csv(
    ctx: TenantContext = Depends(require_permission("finance.reports.view")),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """
    Download the trial balance as a UTF-8 CSV file.

    Columns: Account Code, Account Name, Account Type, Total Debit,
             Total Credit, Net Balance
    """
    tb = FinanceService(db).get_trial_balance(ctx.tenant_id)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["Account Code", "Account Name", "Account Type",
         "Total Debit", "Total Credit", "Net Balance"]
    )
    for line in tb.lines:
        writer.writerow([
            line.account_code,
            line.name,
            line.account_type,
            str(line.total_debit),
            str(line.total_credit),
            str(line.net_balance),
        ])
    # Totals row
    writer.writerow([
        "TOTAL", "", "",
        str(tb.total_debit),
        str(tb.total_credit),
        "BALANCED" if tb.is_balanced else "UNBALANCED",
    ])

    buf.seek(0)
    return StreamingResponse(
        iter([buf.read()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=trial_balance.csv"},
    )


@router.get("/exports/profit-loss.csv")
def export_profit_loss_csv(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    ctx: TenantContext = Depends(require_permission("finance.reports.view")),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Download the Profit & Loss statement as a UTF-8 CSV file."""
    pl = FinanceService(db).get_profit_and_loss(ctx.tenant_id, from_date, to_date)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Item", "Amount"])
    writer.writerow(["Total Revenue",    str(pl.total_revenue)])
    writer.writerow(["Total COGS",       str(pl.total_cogs)])
    writer.writerow(["Gross Profit",     str(pl.gross_profit)])
    writer.writerow(["Total Expenses",   str(pl.total_expenses)])
    writer.writerow(["Net Profit",       str(pl.net_profit)])
    if from_date:
        writer.writerow(["From Date", str(from_date)])
    if to_date:
        writer.writerow(["To Date",   str(to_date)])

    buf.seek(0)
    return StreamingResponse(
        iter([buf.read()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=profit_loss.csv"},
    )
