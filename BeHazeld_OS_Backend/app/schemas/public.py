"""
Public API Pydantic schemas.

These schemas are optimised for external consumers (storefront, mobile apps)
and intentionally expose a smaller, cleaner surface than the internal admin
schemas.  Sensitive internal fields (cost_price, tenant_id) are omitted.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ── Public category response ──────────────────────────────────────────────────

class PublicCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    sort_order: int


# ── Public variant response (price without cost_price) ────────────────────────

class PublicVariantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sku_code: str
    image_url: str | None
    mrp: Decimal
    selling_price: Decimal
    status: str

    @field_validator("image_url", mode="before")
    @classmethod
    def image_url_must_be_string_or_none(cls, v: object) -> str | None:
        if v is None or isinstance(v, str):
            return v
        return None


# ── Public product response ───────────────────────────────────────────────────

class PublicProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_code: str
    name: str
    description: str | None
    image_url: str | None
    status: str
    variants: list[PublicVariantResponse] = []


# ── Paginated wrapper ─────────────────────────────────────────────────────────

class PaginatedProductsResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[PublicProductResponse]


# ── Public customer registration ──────────────────────────────────────────────

class PublicRegisterCustomerRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=250)
    email: str | None = None
    phone: str | None = None
    address: str | None = None


class PublicCustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str | None
    phone: str | None
