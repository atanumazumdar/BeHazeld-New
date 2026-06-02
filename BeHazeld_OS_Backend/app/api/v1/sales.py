"""
Sales router — customers, sale transactions, invoice PDF, bill list.

Permission matrix
-----------------
GET  /customers, /bills, /bills/{id}  : sales.bills.view
POST /customers                       : sales.customers.create
POST /bills  (the main transaction)   : sales.bills.create
GET  /bills/{id}/pdf                  : sales.bills.view
"""
import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from app.api.deps import TenantContext, get_current_tenant, require_permission
from app.db.session import get_db
from app.schemas.sales import (
    CreateCustomerRequest,
    CreateSaleBillRequest,
    CustomerResponse,
    InvoiceMetadata,
    SaleBillResponse,
    SalesInvoiceImportResponse,
)
from app.services.sales_service import SalesService

router = APIRouter(prefix="/sales", tags=["sales"])


# ── Customers ─────────────────────────────────────────────────────────────────

@router.get("/customers", response_model=list[CustomerResponse])
def list_customers(
    search: Optional[str] = Query(None, max_length=100),
    ctx: TenantContext = Depends(require_permission("sales.bills.view")),
    db: Session = Depends(get_db),
) -> list[CustomerResponse]:
    return SalesService(db).list_customers(ctx.tenant_id, search=search)  # type: ignore[return-value]


@router.post(
    "/customers",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_customer(
    body: CreateCustomerRequest,
    ctx: TenantContext = Depends(require_permission("sales.customers.create")),
    db: Session = Depends(get_db),
) -> CustomerResponse:
    return SalesService(db).create_customer(ctx.tenant_id, body)  # type: ignore[return-value]


# ── Sale bills ────────────────────────────────────────────────────────────────

@router.get("/bills", response_model=list[SaleBillResponse])
def list_bills(
    skip: int = 0,
    limit: int = 50,
    customer_id: Optional[uuid.UUID] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    ctx: TenantContext = Depends(require_permission("sales.bills.view")),
    db: Session = Depends(get_db),
) -> list[SaleBillResponse]:
    return SalesService(db).list_bills(  # type: ignore[return-value]
        ctx.tenant_id,
        skip=skip,
        limit=limit,
        customer_id=customer_id,
        date_from=date_from,
        date_to=date_to,
    )


@router.post(
    "/bills",
    response_model=SaleBillResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_sale(
    body: CreateSaleBillRequest,
    ctx: TenantContext = Depends(require_permission("sales.bills.create")),
    db: Session = Depends(get_db),
) -> SaleBillResponse:
    bill, _metadata = SalesService(db).create_sale(
        tenant_id=ctx.tenant_id,
        req=body,
        performed_by_user_id=ctx.user_id,
    )
    return bill  # type: ignore[return-value]


@router.post(
    "/bills/import",
    response_model=SalesInvoiceImportResponse,
)
async def import_sale_bills(
    file: UploadFile = File(...),
    ctx: TenantContext = Depends(require_permission("sales.bills.create")),
    db: Session = Depends(get_db),
) -> SalesInvoiceImportResponse:
    is_csv_filename = bool(file.filename and file.filename.lower().endswith(".csv"))
    is_csv_content = file.content_type in {"text/csv", "application/csv", "application/vnd.ms-excel"}
    if not is_csv_filename and not is_csv_content:
        from app.core.exceptions import ValidationError
        raise ValidationError("Uploaded file must be a CSV")

    try:
        return SalesService(db).import_invoice_csv(
            tenant_id=ctx.tenant_id,
            csv_bytes=await file.read(),
            performed_by_user_id=ctx.user_id,
        )
    except Exception as exc:
        from app.core.exceptions import AppError, ValidationError
        db.rollback()
        if isinstance(exc, AppError):
            raise
        raise ValidationError(f"Sales CSV import failed: {exc}") from exc


@router.get("/bills/{bill_id}", response_model=SaleBillResponse)
def get_bill(
    bill_id: uuid.UUID,
    ctx: TenantContext = Depends(require_permission("sales.bills.view")),
    db: Session = Depends(get_db),
) -> SaleBillResponse:
    return SalesService(db).get_bill(ctx.tenant_id, bill_id)  # type: ignore[return-value]


@router.get(
    "/bills/{bill_id}/pdf",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
def get_invoice_pdf(
    bill_id: uuid.UUID,
    ctx: TenantContext = Depends(require_permission("sales.bills.view")),
    db: Session = Depends(get_db),
) -> Response:
    """Return the invoice as a downloadable PDF."""
    pdf_bytes = SalesService(db).get_invoice_pdf(ctx.tenant_id, bill_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=invoice-{bill_id}.pdf"
        },
    )


@router.get(
    "/bills/{bill_id}/pdf/metadata",
    response_model=InvoiceMetadata,
)
def get_invoice_metadata(
    bill_id: uuid.UUID,
    ctx: TenantContext = Depends(require_permission("sales.bills.view")),
    db: Session = Depends(get_db),
) -> InvoiceMetadata:
    """Return PDF file path and size without streaming the file."""
    from pathlib import Path
    from app.core.config import settings
    bill = SalesService(db).get_bill(ctx.tenant_id, bill_id)
    pdf_path = (
        Path(settings.INVOICE_STORAGE_PATH)
        / str(ctx.tenant_id)
        / f"{bill.invoice_number}.pdf"
    )
    size = pdf_path.stat().st_size if pdf_path.exists() else 0
    return InvoiceMetadata(
        invoice_number=bill.invoice_number,
        file_path=str(pdf_path),
        file_size_bytes=size,
    )
