"""
Purchase router — vendor management, purchase bills, and vendor payments.

Permission matrix
-----------------
GET  /vendors, /bills, /bills/{id}  : purchase.view
POST /vendors                       : purchase.vendors.create
POST /bills                         : purchase.bills.create
POST /payments                      : purchase.payments.create
"""
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import TenantContext, get_current_tenant, require_permission
from app.db.session import get_db
from app.schemas.purchase import (
    CreateTransporterRequest,
    CreateVendorRequest,
    CreatePurchaseBillRequest,
    PurchaseBillResponse,
    RecordVendorPaymentRequest,
    TransporterResponse,
    VendorPaymentResponse,
    VendorResponse,
)
from app.services.purchase_service import PurchaseService

router = APIRouter(prefix="/purchases", tags=["purchases"])


# ── Vendors ───────────────────────────────────────────────────────────────────

@router.get("/vendors", response_model=list[VendorResponse])
def list_vendors(
    ctx: TenantContext = Depends(require_permission("purchase.view")),
    db: Session = Depends(get_db),
) -> list[VendorResponse]:
    return PurchaseService(db).list_vendors(ctx.tenant_id)  # type: ignore[return-value]


@router.post(
    "/vendors",
    response_model=VendorResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_vendor(
    body: CreateVendorRequest,
    ctx: TenantContext = Depends(require_permission("purchase.vendors.create")),
    db: Session = Depends(get_db),
) -> VendorResponse:
    return PurchaseService(db).create_vendor(ctx.tenant_id, body)  # type: ignore[return-value]


# ── Transporters ──────────────────────────────────────────────────────────────

@router.post(
    "/transporters",
    response_model=TransporterResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_transporter(
    body: CreateTransporterRequest,
    ctx: TenantContext = Depends(require_permission("purchase.vendors.create")),
    db: Session = Depends(get_db),
) -> TransporterResponse:
    return PurchaseService(db).create_transporter(ctx.tenant_id, body)  # type: ignore[return-value]


# ── Purchase Bills ────────────────────────────────────────────────────────────

@router.get("/bills", response_model=list[PurchaseBillResponse])
def list_bills(
    skip: int = 0,
    limit: int = 50,
    ctx: TenantContext = Depends(require_permission("purchase.view")),
    db: Session = Depends(get_db),
) -> list[PurchaseBillResponse]:
    return PurchaseService(db).list_bills(ctx.tenant_id, skip=skip, limit=limit)  # type: ignore[return-value]


@router.post(
    "/bills",
    response_model=PurchaseBillResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_purchase_bill(
    body: CreatePurchaseBillRequest,
    ctx: TenantContext = Depends(require_permission("purchase.bills.create")),
    db: Session = Depends(get_db),
) -> PurchaseBillResponse:
    return PurchaseService(db).create_purchase_bill(  # type: ignore[return-value]
        tenant_id=ctx.tenant_id,
        req=body,
        performed_by_user_id=ctx.user_id,
    )


@router.get("/bills/{bill_id}", response_model=PurchaseBillResponse)
def get_bill(
    bill_id: uuid.UUID,
    ctx: TenantContext = Depends(require_permission("purchase.view")),
    db: Session = Depends(get_db),
) -> PurchaseBillResponse:
    return PurchaseService(db).get_bill(ctx.tenant_id, bill_id)  # type: ignore[return-value]


# ── Vendor Payments ───────────────────────────────────────────────────────────

@router.post(
    "/payments",
    response_model=VendorPaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
def record_payment(
    body: RecordVendorPaymentRequest,
    ctx: TenantContext = Depends(require_permission("purchase.payments.create")),
    db: Session = Depends(get_db),
) -> VendorPaymentResponse:
    return PurchaseService(db).record_payment(ctx.tenant_id, body)  # type: ignore[return-value]
