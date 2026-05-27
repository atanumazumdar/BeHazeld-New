from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, model_validator

from app.services.cloudinary_service import TRANSFORMS, build_transform_url


# ── Image ─────────────────────────────────────────────────────────────
class ProductImageRead(BaseModel):
    id: int
    url: str
    alt_text: str
    display_order: int
    is_primary: bool
    # transform_urls is computed from `url` — not stored in DB
    transform_urls: dict[str, str] = {}

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def add_transform_urls(self) -> "ProductImageRead":
        """
        Populate transform_urls from the stored CDN url.
        If the URL is not a Cloudinary URL (e.g. Unsplash), the dict
        contains only the original URL under each key.
        """
        if "/upload/" in self.url:
            self.transform_urls = {
                preset: build_transform_url(self.url, preset)
                for preset in TRANSFORMS
            }
        else:
            self.transform_urls = {preset: self.url for preset in TRANSFORMS}
        return self


# ── Variant ───────────────────────────────────────────────────────────
class ProductVariantRead(BaseModel):
    id: int
    sku: str
    color: str
    size: str
    price_adjustment: Decimal
    stock_count: int
    is_available: bool

    model_config = ConfigDict(from_attributes=True)


# ── Product listing (card view) ───────────────────────────────────────
class ProductRead(BaseModel):
    """Returned in collection listings. Includes primary image + all variants."""

    id: int
    name: str
    slug: str
    description: str
    base_price: Decimal
    is_active: bool
    created_at: datetime
    collection_id: int | None

    primary_image:   ProductImageRead | None
    secondary_image: ProductImageRead | None
    variants:        list[ProductVariantRead]

    # Computed from model @property helpers
    min_price: Decimal
    total_stock: int

    model_config = ConfigDict(from_attributes=True)


# ── Product detail (full page) ────────────────────────────────────────
class ProductDetail(ProductRead):
    """Returned on GET /products/{slug}. Adds the full image gallery."""

    images: list[ProductImageRead]

    model_config = ConfigDict(from_attributes=True)
