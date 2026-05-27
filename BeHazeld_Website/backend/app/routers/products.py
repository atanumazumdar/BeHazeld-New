from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.product import Product
from app.schemas.product import ProductDetail, ProductRead

router = APIRouter(prefix="/products", tags=["products"])


def _product_query(active_only: bool = True):
    """Base select with eager-loaded images and variants."""
    q = (
        select(Product)
        .options(
            selectinload(Product.images),
            selectinload(Product.variants),
        )
    )
    if active_only:
        q = q.where(Product.is_active.is_(True))
    return q


@router.get("/", response_model=list[ProductRead])
def list_products(
    collection: str | None = Query(
        default=None,
        description="Filter by collection slug, e.g. ?collection=campus-muse",
    ),
    db: Session = Depends(get_db),
):
    """
    List active products. Optionally filter by collection slug.

    GET /products/                    → all active products
    GET /products/?collection=slug    → products in that collection
    """
    from app.models.collection import Collection  # local to avoid circular import

    q = _product_query()

    if collection:
        coll = db.scalar(
            select(Collection).where(Collection.slug == collection)
        )
        if coll is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection}' not found",
            )
        q = q.where(Product.collection_id == coll.id)

    products = db.scalars(q.order_by(Product.created_at.desc())).all()
    return products


@router.get("/{slug}", response_model=ProductDetail)
def get_product(slug: str, db: Session = Depends(get_db)):
    """
    Full product detail: all images + all variants.
    Used by the product detail page.
    """
    product = db.scalar(
        _product_query()
        .where(Product.slug == slug)
    )
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return product
