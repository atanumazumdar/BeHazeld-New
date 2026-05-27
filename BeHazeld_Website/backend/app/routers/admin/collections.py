"""
Admin — protected collection CRUD.

Collections control which pages exist on the frontend.
Creating a Collection row with is_active=True is all that is needed
to make a new /collections/{slug} page appear.
"""

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.collection import Collection
from app.models.product import Product
from app.routers.admin.dependencies import require_admin
from app.schemas.admin import CollectionCreate, CollectionUpdate
from app.schemas.collection import CollectionRead, CollectionWithProducts
from app.schemas.product import ProductRead
from app.services import cloudinary_service as cld

router = APIRouter(
    prefix="/admin/collections",
    tags=["admin — collections"],
    dependencies=[Depends(require_admin)],
)


def _get_collection_or_404(collection_id: int, db: Session) -> Collection:
    collection = db.scalar(
        select(Collection).where(Collection.id == collection_id)
    )
    if collection is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"Collection {collection_id} not found",
        )
    return collection


# ── List ─────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=list[CollectionRead],
    summary="List all collections (admin view, includes inactive)",
)
def admin_list_collections(
    include_inactive: bool = Query(default=True),
    db: Session = Depends(get_db),
):
    q = select(Collection).order_by(Collection.display_order)
    if not include_inactive:
        q = q.where(Collection.is_active.is_(True))
    return db.scalars(q).all()


# ── Create ────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=CollectionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new collection",
    description=(
        "Once created with is_active=True, the frontend will serve "
        "GET /collections/{slug} automatically — no code changes needed."
    ),
)
def create_collection(body: CollectionCreate, db: Session = Depends(get_db)):
    existing = db.scalar(select(Collection).where(Collection.slug == body.slug))
    if existing:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Slug '{body.slug}' already exists (id={existing.id})",
        )
    collection = Collection(**body.model_dump())
    db.add(collection)
    db.commit()
    db.refresh(collection)
    return collection


# ── Read ──────────────────────────────────────────────────────────────

@router.get(
    "/{collection_id}",
    response_model=CollectionWithProducts,
    summary="Get a collection with its products (admin view)",
)
def admin_get_collection(collection_id: int, db: Session = Depends(get_db)):
    collection = _get_collection_or_404(collection_id, db)

    products = db.scalars(
        select(Product)
        .where(Product.collection_id == collection.id)
        .options(
            selectinload(Product.images),
            selectinload(Product.variants),
        )
        .order_by(Product.id)
    ).all()

    return CollectionWithProducts(
        **CollectionRead.model_validate(collection).model_dump(),
        products=[ProductRead.model_validate(p) for p in products],
    )


# ── Update ────────────────────────────────────────────────────────────

@router.patch(
    "/{collection_id}",
    response_model=CollectionRead,
    summary="Update a collection (partial — only supplied fields change)",
)
def update_collection(
    collection_id: int,
    body: CollectionUpdate,
    db: Session = Depends(get_db),
):
    collection = _get_collection_or_404(collection_id, db)

    if body.slug and body.slug != collection.slug:
        conflict = db.scalar(select(Collection).where(Collection.slug == body.slug))
        if conflict:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Slug '{body.slug}' already used by collection id={conflict.id}",
            )

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(collection, field, value)

    db.commit()
    db.refresh(collection)
    return collection


# ── Delete / restore ──────────────────────────────────────────────────

@router.delete(
    "/{collection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a collection (hides it and all its products from the store)",
)
def delete_collection(
    collection_id: int,
    hard: bool = Query(default=False, description="Permanently delete (products become uncollected)"),
    db: Session = Depends(get_db),
):
    collection = _get_collection_or_404(collection_id, db)
    if hard:
        db.delete(collection)
    else:
        collection.is_active = False
        # Soft-hide all products in this collection too
        products = db.scalars(
            select(Product).where(Product.collection_id == collection.id)
        ).all()
        for p in products:
            p.is_active = False
    db.commit()


@router.post(
    "/{collection_id}/restore",
    response_model=CollectionRead,
    summary="Restore a soft-deleted collection (does not restore its products)",
)
def restore_collection(collection_id: int, db: Session = Depends(get_db)):
    collection = _get_collection_or_404(collection_id, db)
    collection.is_active = True
    db.commit()
    db.refresh(collection)
    return collection


# ── Re-order ──────────────────────────────────────────────────────────

@router.patch(
    "/{collection_id}/order",
    response_model=CollectionRead,
    summary="Change a collection's display_order (nav position)",
)
def set_display_order(
    collection_id: int,
    display_order: int = Query(ge=0),
    db: Session = Depends(get_db),
):
    collection = _get_collection_or_404(collection_id, db)
    collection.display_order = display_order
    db.commit()
    db.refresh(collection)
    return collection


# ── Hero image upload ─────────────────────────────────────────────────

@router.post(
    "/{collection_id}/hero-image",
    response_model=CollectionRead,
    summary="Upload a collection hero banner → Cloudinary → store CDN URL",
    description=(
        "Accepts `multipart/form-data` with a `file` field (JPEG / PNG / WebP, max 10 MB). "
        "Uploads to `behazeld/collections/{slug}/hero` on Cloudinary and stores the "
        "CDN URL in `collection.hero_image_url`. "
        "Pre-generates a `c_fill,w_1440,h_600` hero transformation eagerly."
    ),
)
async def upload_hero_image(
    collection_id: int,
    file:          UploadFile = File(..., description="Hero banner image (JPEG / PNG / WebP)"),
    db:            Session    = Depends(get_db),
):
    collection = _get_collection_or_404(collection_id, db)

    # ── Validate MIME type ───────────────────────────────────────────
    if file.content_type not in cld.ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Unsupported file type '{file.content_type}'. "
            f"Allowed: {', '.join(sorted(cld.ALLOWED_CONTENT_TYPES))}",
        )

    # ── Validate size ────────────────────────────────────────────────
    file_bytes = await file.read()
    if len(file_bytes) > cld.MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"File too large ({len(file_bytes) / 1_048_576:.1f} MB). "
            f"Maximum: {cld.MAX_FILE_SIZE_MB} MB",
        )

    # ── Upload to Cloudinary ─────────────────────────────────────────
    try:
        result = cld.upload_collection_hero(
            file_bytes      = file_bytes,
            collection_slug = collection.slug,
        )
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            f"Cloudinary upload failed: {exc}",
        ) from exc

    # ── Persist CDN URL ──────────────────────────────────────────────
    collection.hero_image_url = result.secure_url
    db.commit()
    db.refresh(collection)
    return collection
