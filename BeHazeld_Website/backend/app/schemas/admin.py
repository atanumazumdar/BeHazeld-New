"""
Admin request/response schemas.
These are separate from the public read schemas to keep the surface area small
and to allow stricter validation on write operations.
"""

from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


# ── Auth ─────────────────────────────────────────────────────────────

class TokenRequest(BaseModel):
    api_key: str = Field(min_length=8, description="ADMIN_API_KEY value from .env")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86_400   # 24 hours in seconds


# ── Collection ───────────────────────────────────────────────────────

class CollectionCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    slug: str = Field(min_length=2, max_length=140, pattern=r"^[a-z0-9-]+$")
    description: str = Field(default="", max_length=2000)
    hero_image_url: str | None = Field(default=None, max_length=600)
    display_order: int = Field(default=0, ge=0)
    is_active: bool = True


class CollectionUpdate(BaseModel):
    """All fields optional — only supplied fields are updated (PATCH semantics)."""
    name: str | None = Field(default=None, min_length=2, max_length=120)
    slug: str | None = Field(default=None, min_length=2, max_length=140, pattern=r"^[a-z0-9-]+$")
    description: str | None = Field(default=None, max_length=2000)
    hero_image_url: str | None = None
    display_order: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


# ── Product ──────────────────────────────────────────────────────────

class ProductCreate(BaseModel):
    collection_id: int | None = None
    name: str = Field(min_length=2, max_length=120)
    slug: str = Field(min_length=2, max_length=140, pattern=r"^[a-z0-9-]+$")
    description: str = Field(min_length=10, max_length=4000)
    base_price: Decimal = Field(gt=0, decimal_places=2)
    is_active: bool = True


class ProductUpdate(BaseModel):
    """All fields optional — only supplied fields are updated."""
    collection_id: int | None = None
    name: str | None = Field(default=None, min_length=2, max_length=120)
    slug: str | None = Field(default=None, min_length=2, max_length=140, pattern=r"^[a-z0-9-]+$")
    description: str | None = Field(default=None, min_length=10, max_length=4000)
    base_price: Decimal | None = Field(default=None, gt=0, decimal_places=2)
    is_active: bool | None = None


# ── Product variant ──────────────────────────────────────────────────

class VariantCreate(BaseModel):
    sku: str = Field(min_length=3, max_length=80, pattern=r"^[A-Z0-9_-]+$",
                     description="Uppercase SKU, e.g. BH-IBL-IVR-M")
    color: str = Field(min_length=1, max_length=60)
    size: str = Field(min_length=1, max_length=40)
    price_adjustment: Decimal = Field(default=Decimal("0.00"), decimal_places=2,
                                      description="Added to product.base_price. Use negative for discounts.")
    stock_count: int = Field(default=0, ge=0)
    is_available: bool = True

    @field_validator("sku")
    @classmethod
    def sku_uppercase(cls, v: str) -> str:
        return v.upper()


class VariantUpdate(BaseModel):
    """All fields optional."""
    color: str | None = Field(default=None, min_length=1, max_length=60)
    size: str | None = Field(default=None, min_length=1, max_length=40)
    price_adjustment: Decimal | None = Field(default=None, decimal_places=2)
    stock_count: int | None = Field(default=None, ge=0)
    is_available: bool | None = None


class StockAdjust(BaseModel):
    """Convenience body for stock-only updates (restocks, corrections)."""
    delta: int = Field(description="Positive to add stock, negative to remove.")
    reason: str | None = Field(default=None, max_length=200,
                                description="Optional audit note, e.g. 'Restock from supplier'")


# ── Image ────────────────────────────────────────────────────────────

class ImageCreate(BaseModel):
    """Used when adding an image by URL (Cloudinary URL after upload, or external CDN)."""
    url: str = Field(min_length=10, max_length=600)
    alt_text: str = Field(default="", max_length=220)
    display_order: int = Field(default=0, ge=0)
    is_primary: bool = False
