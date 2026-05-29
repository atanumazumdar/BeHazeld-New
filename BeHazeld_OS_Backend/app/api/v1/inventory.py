"""
Inventory router — bin management + stock movement + balance queries.

Permission matrix
-----------------
GET  /bins, /ledger, /balance, /summary : inventory.view
POST /bins                               : inventory.bins.create
POST /movements                          : inventory.stock.adjust
"""
import uuid

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import TenantContext, get_current_tenant, require_permission
from app.core.exceptions import ValidationError
from app.db.session import get_db
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.tenant_repository import TenantRepository
from app.schemas.inventory import (
    BinResponse,
    CreateBinRequest,
    InventoryLocationImportResponse,
    LocationResponse,
    RecordMovementRequest,
    StockBalanceResponse,
    StockMovementResponse,
)
from app.services.inventory_service import InventoryService

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.post(
    "/import/locations-bins",
    response_model=InventoryLocationImportResponse,
)
async def import_locations_bins(
    file: UploadFile = File(...),
    ctx: TenantContext = Depends(require_permission("inventory.bins.create")),
    db: Session = Depends(get_db),
) -> InventoryLocationImportResponse:
    is_csv_filename = bool(file.filename and file.filename.lower().endswith(".csv"))
    is_csv_content = file.content_type in {"text/csv", "application/csv", "application/vnd.ms-excel"}
    if not is_csv_filename and not is_csv_content:
        raise ValidationError("Uploaded file must be a CSV")

    try:
        return InventoryService(db).import_locations_bins_csv(ctx.tenant_id, await file.read())
    except ValueError as exc:
        db.rollback()
        raise ValidationError(str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise ValidationError(f"CSV import failed: {exc}") from exc


# ── Bins ──────────────────────────────────────────────────────────────────────

@router.get(
    "/locations/{location_id}/bins",
    response_model=list[BinResponse],
)
def list_bins(
    location_id: uuid.UUID,
    ctx: TenantContext = Depends(require_permission("inventory.view")),
    db: Session = Depends(get_db),
) -> list[BinResponse]:
    return InventoryService(db).list_bins(ctx.tenant_id, location_id)  # type: ignore[return-value]


@router.post(
    "/locations/{location_id}/bins",
    response_model=BinResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_bin(
    location_id: uuid.UUID,
    body: CreateBinRequest,
    ctx: TenantContext = Depends(require_permission("inventory.bins.create")),
    db: Session = Depends(get_db),
) -> BinResponse:
    return InventoryService(db).create_bin(ctx.tenant_id, location_id, body)  # type: ignore[return-value]


# ── Locations ─────────────────────────────────────────────────────────────────

@router.get(
    "/locations",
    response_model=list[LocationResponse],
)
def list_locations(
    ctx: TenantContext = Depends(require_permission("inventory.view")),
    db: Session = Depends(get_db),
) -> list[LocationResponse]:
    """List all active locations for the tenant, with their bins."""
    locations = TenantRepository(db).list_locations_by_tenant(ctx.tenant_id)
    inv_repo = InventoryRepository(db)
    result = []
    for loc in locations:
        bins = inv_repo.list_bins_by_location(ctx.tenant_id, loc.id)
        loc_data = LocationResponse.model_validate(loc)
        loc_data.bins = [BinResponse.model_validate(b) for b in bins]
        result.append(loc_data)
    return result


# ── Stock movements ───────────────────────────────────────────────────────────

@router.post(
    "/movements",
    response_model=StockMovementResponse,
    status_code=status.HTTP_201_CREATED,
)
def record_movement(
    body: RecordMovementRequest,
    ctx: TenantContext = Depends(require_permission("inventory.stock.adjust")),
    db: Session = Depends(get_db),
) -> StockMovementResponse:
    return InventoryService(db).record_stock_movement(  # type: ignore[return-value]
        tenant_id=ctx.tenant_id,
        req=body,
        performed_by_user_id=ctx.user_id,
    )


# ── Balance / ledger queries ──────────────────────────────────────────────────

@router.get(
    "/balance",
    response_model=StockBalanceResponse | None,
)
def get_balance(
    product_variant_id: uuid.UUID,
    location_id: uuid.UUID,
    bin_id: uuid.UUID,
    ctx: TenantContext = Depends(require_permission("inventory.view")),
    db: Session = Depends(get_db),
) -> StockBalanceResponse | None:
    return InventoryService(db).get_balance(  # type: ignore[return-value]
        ctx.tenant_id, product_variant_id, location_id, bin_id
    )


@router.get(
    "/summary/{product_variant_id}",
    response_model=list[StockBalanceResponse],
)
def get_stock_summary(
    product_variant_id: uuid.UUID,
    ctx: TenantContext = Depends(require_permission("inventory.view")),
    db: Session = Depends(get_db),
) -> list[StockBalanceResponse]:
    return InventoryService(db).get_stock_summary(ctx.tenant_id, product_variant_id)  # type: ignore[return-value]


@router.get(
    "/ledger/{product_variant_id}",
    response_model=list[StockMovementResponse],
)
def get_ledger(
    product_variant_id: uuid.UUID,
    location_id: uuid.UUID,
    limit: int = 100,
    ctx: TenantContext = Depends(require_permission("inventory.view")),
    db: Session = Depends(get_db),
) -> list[StockMovementResponse]:
    return InventoryService(db).get_ledger(  # type: ignore[return-value]
        ctx.tenant_id, product_variant_id, location_id, limit=limit
    )
