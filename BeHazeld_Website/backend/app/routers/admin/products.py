"""
Admin — protected product & variant CRUD.

All endpoints require either:
  • Authorization: Bearer <jwt>   (obtained from POST /admin/auth/token)
  • X-API-Key: <ADMIN_API_KEY>

Product soft-delete: sets is_active=False so order history and URLs remain intact.
To permanently delete, call DELETE with ?hard=true.
"""

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.product import Product
from app.models.product_image import ProductImage
from app.models.product_variant import ProductVariant
from app.routers.admin.dependencies import require_admin
from app.schemas.admin import (
    ImageCreate,
    ProductCreate,
    ProductUpdate,
    StockAdjust,
    VariantCreate,
    VariantUpdate,
)
from app.schemas.product import ProductDetail, ProductImageRead, ProductVariantRead
from app.services import cloudinary_service as cld

router = APIRouter(
    prefix="/admin/products",
    tags=["admin — products"],
    dependencies=[Depends(require_admin)],
)


# ── Helpers ──────────────────────────────────────────────────────────
def _get_product_or_404(product_id: int, db: Session) -> Product:
    product = db.scalar(
        select(Product)
        .where(Product.id == product_id)
        .options(selectinload(Product.images), selectinload(Product.variants))
    )
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Product {product_id} not found")
    return product


def _get_variant_or_404(variant_id: int, product_id: int, db: Session) -> ProductVariant:
    variant = db.scalar(
        select(ProductVariant).where(
            ProductVariant.id == variant_id,
            ProductVariant.product_id == product_id,
        )
    )
    if variant is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"Variant {variant_id} not found on product {product_id}",
        )
    return variant


# ════════════════════════════════════════════════════════════════════
# PRODUCT CRUD
# ════════════════════════════════════════════════════════════════════

@router.get("/", response_model=list[ProductDetail], summary="List all products (admin view, includes inactive)")
def admin_list_products(
    include_inactive: bool = Query(default=True),
    db: Session = Depends(get_db),
):
    q = select(Product).options(
        selectinload(Product.images), selectinload(Product.variants)
    )
    if not include_inactive:
        q = q.where(Product.is_active.is_(True))
    return db.scalars(q.order_by(Product.created_at.desc())).all()


@router.post(
    "/",
    response_model=ProductDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product",
)
def create_product(body: ProductCreate, db: Session = Depends(get_db)):
    # Slug uniqueness check
    existing = db.scalar(select(Product).where(Product.slug == body.slug))
    if existing:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"A product with slug '{body.slug}' already exists (id={existing.id})",
        )
    product = Product(**body.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.get("/{product_id}", response_model=ProductDetail, summary="Get a single product (admin)")
def admin_get_product(product_id: int, db: Session = Depends(get_db)):
    return _get_product_or_404(product_id, db)


@router.patch(
    "/{product_id}",
    response_model=ProductDetail,
    summary="Update a product (partial — only supplied fields change)",
)
def update_product(product_id: int, body: ProductUpdate, db: Session = Depends(get_db)):
    product = _get_product_or_404(product_id, db)

    # Slug uniqueness check (only if slug is being changed)
    if body.slug and body.slug != product.slug:
        conflict = db.scalar(select(Product).where(Product.slug == body.slug))
        if conflict:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Slug '{body.slug}' is already used by product id={conflict.id}",
            )

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a product (sets is_active=False). Pass ?hard=true to permanently delete.",
)
def delete_product(
    product_id: int,
    hard: bool = Query(default=False, description="Permanently delete instead of soft-delete"),
    db: Session = Depends(get_db),
):
    product = _get_product_or_404(product_id, db)
    if hard:
        db.delete(product)
    else:
        product.is_active = False
    db.commit()


@router.post(
    "/{product_id}/restore",
    response_model=ProductDetail,
    summary="Restore a soft-deleted product",
)
def restore_product(product_id: int, db: Session = Depends(get_db)):
    product = _get_product_or_404(product_id, db)
    product.is_active = True
    db.commit()
    db.refresh(product)
    return product


# ════════════════════════════════════════════════════════════════════
# VARIANT CRUD
# ════════════════════════════════════════════════════════════════════

@router.post(
    "/{product_id}/variants",
    response_model=ProductVariantRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a variant (size/colour/SKU) to a product",
)
def add_variant(product_id: int, body: VariantCreate, db: Session = Depends(get_db)):
    _get_product_or_404(product_id, db)   # validates product exists

    # SKU uniqueness
    sku_conflict = db.scalar(
        select(ProductVariant).where(ProductVariant.sku == body.sku)
    )
    if sku_conflict:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"SKU '{body.sku}' already exists (variant id={sku_conflict.id})",
        )

    variant = ProductVariant(product_id=product_id, **body.model_dump())
    db.add(variant)
    db.commit()
    db.refresh(variant)
    return variant


@router.patch(
    "/{product_id}/variants/{variant_id}",
    response_model=ProductVariantRead,
    summary="Update a variant (partial)",
)
def update_variant(
    product_id: int,
    variant_id: int,
    body: VariantUpdate,
    db: Session = Depends(get_db),
):
    variant = _get_variant_or_404(variant_id, product_id, db)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(variant, field, value)
    db.commit()
    db.refresh(variant)
    return variant


@router.post(
    "/{product_id}/variants/{variant_id}/stock",
    response_model=ProductVariantRead,
    summary="Adjust variant stock (delta + audit reason)",
)
def adjust_stock(
    product_id: int,
    variant_id: int,
    body: StockAdjust,
    db: Session = Depends(get_db),
):
    variant = _get_variant_or_404(variant_id, product_id, db)
    new_count = variant.stock_count + body.delta
    if new_count < 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Adjustment would set stock to {new_count}. Current stock: {variant.stock_count}",
        )
    variant.stock_count = new_count
    # Auto-toggle availability
    if new_count == 0:
        variant.is_available = False
    elif not variant.is_available:
        variant.is_available = True
    db.commit()
    db.refresh(variant)
    return variant


@router.delete(
    "/{product_id}/variants/{variant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Permanently delete a variant",
)
def delete_variant(product_id: int, variant_id: int, db: Session = Depends(get_db)):
    variant = _get_variant_or_404(variant_id, product_id, db)
    db.delete(variant)
    db.commit()


# ════════════════════════════════════════════════════════════════════
# IMAGE MANAGEMENT
# ════════════════════════════════════════════════════════════════════

@router.post(
    "/{product_id}/images/upload",
    response_model=ProductImageRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload an image file → Cloudinary → store CDN URL",
    description=(
        "Accepts `multipart/form-data` with a `file` field (JPEG / PNG / WebP, max 10 MB). "
        "The file is uploaded to Cloudinary under `behazeld/products/{slug}/`, "
        "and the returned CDN URL is saved to `product_images`. "
        "Requires `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` in .env."
    ),
)
async def upload_product_image(
    product_id:    int,
    file:          UploadFile = File(..., description="Image file (JPEG / PNG / WebP)"),
    alt_text:      str        = Form(default=""),
    display_order: int        = Form(default=0, ge=0),
    is_primary:    bool       = Form(default=False),
    db:            Session    = Depends(get_db),
):
    product = _get_product_or_404(product_id, db)

    # ── Validate MIME type ───────────────────────────────────────────
    if file.content_type not in cld.ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Unsupported file type '{file.content_type}'. "
            f"Allowed: {', '.join(sorted(cld.ALLOWED_CONTENT_TYPES))}",
        )

    # ── Validate file size ───────────────────────────────────────────
    file_bytes = await file.read()
    if len(file_bytes) > cld.MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"File too large ({len(file_bytes) / 1_048_576:.1f} MB). "
            f"Maximum allowed: {cld.MAX_FILE_SIZE_MB} MB",
        )

    # ── Upload to Cloudinary ─────────────────────────────────────────
    try:
        result = cld.upload_product_image(
            file_bytes    = file_bytes,
            product_slug  = product.slug,
            display_order = display_order,
            is_primary    = is_primary,
        )
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            f"Cloudinary upload failed: {exc}",
        ) from exc

    # ── Demote existing primary if needed ────────────────────────────
    if is_primary:
        for img in db.scalars(
            select(ProductImage).where(
                ProductImage.product_id == product_id,
                ProductImage.is_primary.is_(True),
            )
        ).all():
            img.is_primary = False

    # ── Save to DB ───────────────────────────────────────────────────
    image = ProductImage(
        product_id    = product.id,
        url           = result.secure_url,
        alt_text      = alt_text or f"{product.name} — image {display_order + 1}",
        display_order = display_order,
        is_primary    = is_primary,
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    return image


@router.post(
    "/{product_id}/images",
    response_model=ProductImageRead,
    status_code=status.HTTP_201_CREATED,
    summary="Attach an image by URL (Cloudinary URL, external CDN, or Unsplash)",
)
def add_image_by_url(product_id: int, body: ImageCreate, db: Session = Depends(get_db)):
    _get_product_or_404(product_id, db)

    # If this is marked primary, demote existing primaries
    if body.is_primary:
        existing_primary = db.scalars(
            select(ProductImage).where(
                ProductImage.product_id == product_id,
                ProductImage.is_primary.is_(True),
            )
        ).all()
        for img in existing_primary:
            img.is_primary = False

    image = ProductImage(product_id=product_id, **body.model_dump())
    db.add(image)
    db.commit()
    db.refresh(image)
    return image


@router.delete(
    "/{product_id}/images/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an image record (does not delete from Cloudinary)",
)
def delete_image(product_id: int, image_id: int, db: Session = Depends(get_db)):
    image = db.scalar(
        select(ProductImage).where(
            ProductImage.id == image_id,
            ProductImage.product_id == product_id,
        )
    )
    if image is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Image {image_id} not found")
    db.delete(image)
    db.commit()
