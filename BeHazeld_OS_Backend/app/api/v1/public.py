"""
Public Catalog API — no authentication required.

All endpoints are read-only for the catalog (no writes to product data).
Customer self-registration is the only write endpoint.

Route design
------------
Every route takes `tenant_id` as a path parameter so this API can serve
multiple tenants from the same deployment.  The storefront embeds the
tenant's UUID in its build config.

GET  /{tenant_id}/products                   — paginated active products
GET  /{tenant_id}/products/{product_id}      — single product + variants
GET  /{tenant_id}/categories                 — category list (flat)
POST /{tenant_id}/customers/register         — customer self-registration

Performance notes
-----------------
* PublicRepository uses Core SELECT (no lazy loads).
* Variant list is loaded in a second targeted query (avoids N+1 on product list).
* No joinedload on the product list — only product-level data is returned in
  the list; full detail (with variants) is returned on GET /{product_id}.
"""
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.public_repository import PublicRepository
from app.repositories.sales_repository import SalesRepository
from app.schemas.public import (
    PaginatedProductsResponse,
    PublicCategoryResponse,
    PublicCustomerResponse,
    PublicProductResponse,
    PublicRegisterCustomerRequest,
    PublicVariantResponse,
)

router = APIRouter(prefix="/public", tags=["public"])


# ── Products ──────────────────────────────────────────────────────────────────

@router.get(
    "/{tenant_id}/products",
    response_model=PaginatedProductsResponse,
)
def list_public_products(
    tenant_id: uuid.UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    category_id: uuid.UUID | None = Query(default=None),
    search: str | None = Query(default=None, max_length=100),
    db: Session = Depends(get_db),
) -> PaginatedProductsResponse:
    """
    List active products for a tenant.

    Supports optional filtering by category and keyword search on name / code.
    Returns a paginated envelope with `total` count for the client to drive
    pagination controls.
    """
    repo = PublicRepository(db)
    products = repo.list_active_products(
        tenant_id,
        category_id=category_id,
        search=search,
        skip=skip,
        limit=limit,
    )
    total = repo.count_active_products(
        tenant_id, category_id=category_id, search=search
    )
    # Enrich each product with its active variants (second targeted query per product)
    items = []
    for p in products:
        variants = repo.list_active_variants_for_product(tenant_id, p.id)
        items.append(
            PublicProductResponse(
                id=p.id,
                product_code=p.product_code,
                name=p.name,
                description=p.description,
                image_url=p.image_url,
                status=p.status,
                variants=[
                    PublicVariantResponse(
                        id=v.id,
                        sku_code=v.sku_code,
                        image_url=v.image_url,
                        mrp=v.mrp,
                        selling_price=v.selling_price,
                        status=v.status,
                    )
                    for v in variants
                ],
            )
        )

    return PaginatedProductsResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=items,
    )


@router.get(
    "/{tenant_id}/products/{product_id}",
    response_model=PublicProductResponse,
)
def get_public_product(
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> PublicProductResponse:
    """Return a single active product with all its active variants."""
    from app.core.exceptions import NotFoundError
    from sqlalchemy import select
    from app.models.catalog import Product

    stmt = (
        select(Product)
        .where(
            Product.id == product_id,
            Product.tenant_id == tenant_id,
            Product.status == "active",
        )
    )
    product = db.execute(stmt).scalar_one_or_none()
    if product is None:
        raise NotFoundError(f"Product {product_id} not found")

    repo = PublicRepository(db)
    variants = repo.list_active_variants_for_product(tenant_id, product_id)

    return PublicProductResponse(
        id=product.id,
        product_code=product.product_code,
        name=product.name,
        description=product.description,
        image_url=product.image_url,
        status=product.status,
        variants=[
            PublicVariantResponse(
                id=v.id,
                sku_code=v.sku_code,
                image_url=v.image_url,
                mrp=v.mrp,
                selling_price=v.selling_price,
                status=v.status,
            )
            for v in variants
        ],
    )


# ── Categories ────────────────────────────────────────────────────────────────

@router.get(
    "/{tenant_id}/categories",
    response_model=list[PublicCategoryResponse],
)
def list_public_categories(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> list[PublicCategoryResponse]:
    """Return all active categories in sort_order for the storefront nav."""
    return PublicRepository(db).list_active_categories(tenant_id)  # type: ignore[return-value]


# ── Customer self-registration ────────────────────────────────────────────────

@router.post(
    "/{tenant_id}/customers/register",
    response_model=PublicCustomerResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_customer(
    tenant_id: uuid.UUID,
    body: PublicRegisterCustomerRequest,
    db: Session = Depends(get_db),
) -> PublicCustomerResponse:
    """
    Allow a customer to create their own profile.
    No authentication required — uses the SalesRepository directly.
    """
    try:
        customer = SalesRepository(db).create_customer(
            tenant_id=tenant_id,
            name=body.name,
            email=body.email,
            phone=body.phone,
            address=body.address,
        )
        db.commit()
        db.refresh(customer)
        return customer  # type: ignore[return-value]
    except Exception:
        db.rollback()
        raise
