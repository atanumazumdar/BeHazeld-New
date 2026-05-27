from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.collection import Collection
from app.models.product import Product
from app.schemas.collection import CollectionRead, CollectionWithProducts
from app.schemas.product import ProductRead

router = APIRouter(prefix="/collections", tags=["collections"])


def _load_active_products(collection_id: int, db: Session) -> list[Product]:
    """
    Fetch active products for a collection, eagerly loading images + variants.
    Keeps the 'is_active' filter out of the ORM relationship so eager loading
    works correctly with selectinload.
    """
    return list(
        db.scalars(
            select(Product)
            .where(
                Product.collection_id == collection_id,
                Product.is_active.is_(True),
            )
            .options(
                selectinload(Product.images),
                selectinload(Product.variants),
            )
            .order_by(Product.id)
        ).all()
    )


@router.get("/", response_model=list[CollectionRead])
def list_collections(db: Session = Depends(get_db)):
    """
    Return all active collections ordered by display_order.
    Used by the frontend nav and the /atelier editorial page.
    """
    collections = db.scalars(
        select(Collection)
        .where(Collection.is_active.is_(True))
        .order_by(Collection.display_order)
    ).all()
    return collections


@router.get("/{slug}", response_model=CollectionWithProducts)
def get_collection(slug: str, db: Session = Depends(get_db)):
    """
    Return a collection and all its active products (with images + variants).

    This is the key endpoint for dynamic collection pages:
    adding a Product row with this collection's id automatically
    updates the response — no frontend code changes required.
    """
    collection = db.scalar(
        select(Collection)
        .where(Collection.slug == slug, Collection.is_active.is_(True))
    )
    if collection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection '{slug}' not found",
        )

    products = _load_active_products(collection.id, db)

    # Build the response by composing the two pieces explicitly.
    # This avoids relying on the ORM relationship (which doesn't filter
    # is_active without a custom primaryjoin).
    return CollectionWithProducts(
        **CollectionRead.model_validate(collection).model_dump(),
        products=[ProductRead.model_validate(p) for p in products],
    )
