"""
Catalog router — master data + product + variant CRUD.

Permission matrix
-----------------
GET  endpoints : catalog.view          (read-only access)
POST endpoints : catalog.products.create  (product creation)
DELETE         : catalog.products.delete
POST /variants : catalog.variants.create
DELETE /variants: catalog.variants.delete
Master creates : catalog.masters.create
"""
import uuid

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import TenantContext, get_current_tenant, require_permission
from app.db.session import get_db
from app.core.exceptions import ValidationError
from app.schemas.catalog import (
    BrandResponse,
    CategoryResponse,
    ColorResponse,
    CreateBrandRequest,
    CreateCategoryRequest,
    CreateColorRequest,
    CreateProductGroupRequest,
    CreateProductRequest,
    CreateProductTypeRequest,
    CreateSizeRequest,
    CreateVariantRequest,
    MasterDataImportResponse,
    ProductGroupResponse,
    ProductResponse,
    ProductTypeResponse,
    ProductVariantResponse,
    SizeResponse,
)
from app.services.catalog_service import CatalogService

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.post(
    "/import/master-data",
    response_model=MasterDataImportResponse,
)
async def import_master_data(
    entity_type: str,
    file: UploadFile = File(...),
    ctx: TenantContext = Depends(require_permission("catalog.masters.create")),
    db: Session = Depends(get_db),
) -> MasterDataImportResponse:
    is_csv_filename = bool(file.filename and file.filename.lower().endswith(".csv"))
    is_csv_content = file.content_type in {"text/csv", "application/csv", "application/vnd.ms-excel"}
    if not is_csv_filename and not is_csv_content:
        raise ValidationError("Uploaded file must be a CSV")
    try:
        return CatalogService(db).import_master_data_csv(
            ctx.tenant_id,
            entity_type,
            await file.read(),
        )
    except ValueError as exc:
        db.rollback()
        raise ValidationError(str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise ValidationError(f"CSV import failed: {exc}") from exc


# ── master data — categories ──────────────────────────────────────────────────

@router.get("/categories", response_model=list[CategoryResponse])
def list_categories(
    ctx: TenantContext = Depends(require_permission("catalog.view")),
    db: Session = Depends(get_db),
) -> list[CategoryResponse]:
    return CatalogService(db).list_categories(ctx.tenant_id)  # type: ignore[return-value]


@router.post(
    "/categories",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_category(
    body: CreateCategoryRequest,
    ctx: TenantContext = Depends(require_permission("catalog.masters.create")),
    db: Session = Depends(get_db),
) -> CategoryResponse:
    return CatalogService(db).create_category(ctx.tenant_id, body)  # type: ignore[return-value]


# ── master data — product groups ──────────────────────────────────────────────

@router.get("/product-groups", response_model=list[ProductGroupResponse])
def list_product_groups(
    ctx: TenantContext = Depends(require_permission("catalog.view")),
    db: Session = Depends(get_db),
) -> list[ProductGroupResponse]:
    return CatalogService(db).list_product_groups(ctx.tenant_id)  # type: ignore[return-value]


@router.post(
    "/product-groups",
    response_model=ProductGroupResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product_group(
    body: CreateProductGroupRequest,
    ctx: TenantContext = Depends(require_permission("catalog.masters.create")),
    db: Session = Depends(get_db),
) -> ProductGroupResponse:
    return CatalogService(db).create_product_group(ctx.tenant_id, body)  # type: ignore[return-value]


# ── master data — product types ───────────────────────────────────────────────

@router.get("/product-types", response_model=list[ProductTypeResponse])
def list_product_types(
    ctx: TenantContext = Depends(require_permission("catalog.view")),
    db: Session = Depends(get_db),
) -> list[ProductTypeResponse]:
    return CatalogService(db).list_product_types(ctx.tenant_id)  # type: ignore[return-value]


@router.post(
    "/product-types",
    response_model=ProductTypeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product_type(
    body: CreateProductTypeRequest,
    ctx: TenantContext = Depends(require_permission("catalog.masters.create")),
    db: Session = Depends(get_db),
) -> ProductTypeResponse:
    return CatalogService(db).create_product_type(ctx.tenant_id, body)  # type: ignore[return-value]


# ── master data — brands ──────────────────────────────────────────────────────

@router.get("/brands", response_model=list[BrandResponse])
def list_brands(
    ctx: TenantContext = Depends(require_permission("catalog.view")),
    db: Session = Depends(get_db),
) -> list[BrandResponse]:
    return CatalogService(db).list_brands(ctx.tenant_id)  # type: ignore[return-value]


@router.post(
    "/brands",
    response_model=BrandResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_brand(
    body: CreateBrandRequest,
    ctx: TenantContext = Depends(require_permission("catalog.masters.create")),
    db: Session = Depends(get_db),
) -> BrandResponse:
    return CatalogService(db).create_brand(ctx.tenant_id, body)  # type: ignore[return-value]


# ── master data — sizes ───────────────────────────────────────────────────────

@router.get("/sizes", response_model=list[SizeResponse])
def list_sizes(
    ctx: TenantContext = Depends(require_permission("catalog.view")),
    db: Session = Depends(get_db),
) -> list[SizeResponse]:
    return CatalogService(db).list_sizes(ctx.tenant_id)  # type: ignore[return-value]


@router.post(
    "/sizes",
    response_model=SizeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_size(
    body: CreateSizeRequest,
    ctx: TenantContext = Depends(require_permission("catalog.masters.create")),
    db: Session = Depends(get_db),
) -> SizeResponse:
    return CatalogService(db).create_size(ctx.tenant_id, body)  # type: ignore[return-value]


# ── master data — colors ──────────────────────────────────────────────────────

@router.get("/colors", response_model=list[ColorResponse])
def list_colors(
    ctx: TenantContext = Depends(require_permission("catalog.view")),
    db: Session = Depends(get_db),
) -> list[ColorResponse]:
    return CatalogService(db).list_colors(ctx.tenant_id)  # type: ignore[return-value]


@router.post(
    "/colors",
    response_model=ColorResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_color(
    body: CreateColorRequest,
    ctx: TenantContext = Depends(require_permission("catalog.masters.create")),
    db: Session = Depends(get_db),
) -> ColorResponse:
    return CatalogService(db).create_color(ctx.tenant_id, body)  # type: ignore[return-value]


# ── products ──────────────────────────────────────────────────────────────────

@router.get("/products", response_model=list[ProductResponse])
def list_products(
    skip: int = 0,
    limit: int = 50,
    status: str = "active",
    search: str | None = None,
    category_id: uuid.UUID | None = None,
    brand_id: uuid.UUID | None = None,
    ctx: TenantContext = Depends(require_permission("catalog.view")),
    db: Session = Depends(get_db),
) -> list[ProductResponse]:
    return CatalogService(db).list_products(  # type: ignore[return-value]
        ctx.tenant_id,
        status=status,
        skip=skip,
        limit=limit,
        search=search,
        category_id=category_id,
        brand_id=brand_id,
    )


@router.post(
    "/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product(
    body: CreateProductRequest,
    ctx: TenantContext = Depends(require_permission("catalog.products.create")),
    db: Session = Depends(get_db),
) -> ProductResponse:
    return CatalogService(db).create_product(ctx.tenant_id, body)  # type: ignore[return-value]


@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: uuid.UUID,
    ctx: TenantContext = Depends(require_permission("catalog.view")),
    db: Session = Depends(get_db),
) -> ProductResponse:
    return CatalogService(db).get_product(ctx.tenant_id, product_id)  # type: ignore[return-value]


@router.post(
    "/products/{product_id}/image",
    response_model=ProductResponse,
)
def upload_product_image(
    product_id: uuid.UUID,
    image: UploadFile = File(...),
    ctx: TenantContext = Depends(require_permission("catalog.products.create")),
    db: Session = Depends(get_db),
) -> ProductResponse:
    if not image.content_type or not image.content_type.startswith("image/"):
        raise ValidationError("Uploaded file must be an image")
    return CatalogService(db).upload_product_image(
        ctx.tenant_id,
        product_id,
        image.file,
        filename=image.filename,
    )  # type: ignore[return-value]


@router.delete(
    "/products/{product_id}",
    response_model=ProductResponse,
)
def delete_product(
    product_id: uuid.UUID,
    ctx: TenantContext = Depends(require_permission("catalog.products.delete")),
    db: Session = Depends(get_db),
) -> ProductResponse:
    return CatalogService(db).soft_delete_product(ctx.tenant_id, product_id)  # type: ignore[return-value]


# ── variants ──────────────────────────────────────────────────────────────────

@router.get(
    "/products/{product_id}/variants",
    response_model=list[ProductVariantResponse],
)
def list_variants(
    product_id: uuid.UUID,
    ctx: TenantContext = Depends(require_permission("catalog.view")),
    db: Session = Depends(get_db),
) -> list[ProductVariantResponse]:
    return CatalogService(db).list_variants(ctx.tenant_id, product_id)  # type: ignore[return-value]


@router.post(
    "/products/{product_id}/variants",
    response_model=ProductVariantResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_variant(
    product_id: uuid.UUID,
    body: CreateVariantRequest,
    ctx: TenantContext = Depends(require_permission("catalog.variants.create")),
    db: Session = Depends(get_db),
) -> ProductVariantResponse:
    return CatalogService(db).create_variant(ctx.tenant_id, product_id, body)  # type: ignore[return-value]


@router.post(
    "/products/{product_id}/variants/{variant_id}/image",
    response_model=ProductVariantResponse,
)
def upload_variant_image(
    product_id: uuid.UUID,
    variant_id: uuid.UUID,
    image: UploadFile = File(...),
    ctx: TenantContext = Depends(require_permission("catalog.variants.create")),
    db: Session = Depends(get_db),
) -> ProductVariantResponse:
    if not image.content_type or not image.content_type.startswith("image/"):
        raise ValidationError("Uploaded file must be an image")
    return CatalogService(db).upload_variant_image(
        ctx.tenant_id,
        product_id,
        variant_id,
        image.file,
        filename=image.filename,
    )  # type: ignore[return-value]


@router.delete(
    "/products/{product_id}/variants/{variant_id}",
    response_model=ProductVariantResponse,
)
def delete_variant(
    product_id: uuid.UUID,
    variant_id: uuid.UUID,
    ctx: TenantContext = Depends(require_permission("catalog.variants.delete")),
    db: Session = Depends(get_db),
) -> ProductVariantResponse:
    return CatalogService(db).soft_delete_variant(ctx.tenant_id, variant_id)  # type: ignore[return-value]
