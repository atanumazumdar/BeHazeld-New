"""
Public API Pydantic schemas.

These schemas are optimised for external consumers (storefront, mobile apps)
and intentionally expose a smaller, cleaner surface than the internal admin
schemas.  Sensitive internal fields (cost_price, tenant_id) are omitted.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.common import StrictRequestModel, validate_phone_number


# ── Public category response ──────────────────────────────────────────────────

class PublicCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    sort_order: int


class PublicProductGroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None


# ── Public variant response (price without cost_price) ────────────────────────

class PublicVariantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sku_code: str
    size_id: uuid.UUID
    size_name: str
    color_id: uuid.UUID
    color_name: str
    color_hex_code: str | None
    fabric: str | None
    image_url: str | None
    mrp: Decimal
    selling_price: Decimal
    stock_count: Decimal
    is_available: bool
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
    category_id: uuid.UUID | None
    category_name: str | None = None
    product_group_id: uuid.UUID | None
    product_group_name: str | None = None
    product_type_id: uuid.UUID | None
    brand_id: uuid.UUID | None
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

class PublicRegisterCustomerRequest(StrictRequestModel):
    name: str = Field(..., min_length=1, max_length=250)
    email: EmailStr | None = None
    phone: Annotated[str | None, Field(max_length=20)] = None
    address: Annotated[str | None, Field(max_length=500)] = None

    @field_validator("phone")
    @classmethod
    def phone_must_be_bounded(cls, value: str | None) -> str | None:
        return validate_phone_number(value)


class PublicCustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str | None
    phone: str | None


# ── Public checkout ───────────────────────────────────────────────────────────

class PublicCheckoutItemRequest(StrictRequestModel):
    product_variant_id: uuid.UUID
    quantity: Annotated[int, Field(gt=0, le=99)]


class PublicCheckoutRequest(StrictRequestModel):
    customer_name: Annotated[str, Field(min_length=1, max_length=250)]
    customer_email: EmailStr | None = None
    customer_phone: Annotated[str | None, Field(max_length=20)] = None
    shipping_address: Annotated[str, Field(min_length=1, max_length=500)]
    city: Annotated[str, Field(min_length=1, max_length=100)]
    state: Annotated[str, Field(min_length=1, max_length=100)]
    postal_code: Annotated[str, Field(min_length=1, max_length=20)]
    country: Annotated[str, Field(min_length=1, max_length=100)] = "India"
    total_amount: Annotated[Decimal, Field(gt=0)]
    items: Annotated[list[PublicCheckoutItemRequest], Field(min_length=1)]

    @field_validator("customer_phone")
    @classmethod
    def phone_must_be_bounded(cls, value: str | None) -> str | None:
        return validate_phone_number(value)


class PublicCheckoutResponse(BaseModel):
    order_id: str
    total_amount: Decimal
    order_summary: str
    whatsapp_message: str
