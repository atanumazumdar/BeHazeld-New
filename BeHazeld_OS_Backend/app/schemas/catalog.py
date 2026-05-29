"""
Catalog Pydantic schemas — request validation and response serialization.

Validation rules
----------------
- name fields: min_length=1 (reject empty strings)
- sort_order / reorder_level: ge=0 (non-negative integers)
- mrp / selling_price / cost_price: gt=0 (strictly positive Decimal)
- hex_code: must match #RRGGBB if provided
- image_url: max_length=500
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ── Request schemas ───────────────────────────────────────────────────────────

class CreateCategoryRequest(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=150)]
    description: str | None = None
    sort_order: Annotated[int, Field(ge=0)] = 0


class CreateProductGroupRequest(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=150)]
    description: str | None = None


class CreateProductTypeRequest(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=150)]


class CreateBrandRequest(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=150)]


class CreateSizeRequest(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=50)]
    sort_order: Annotated[int, Field(ge=0)] = 0


class CreateColorRequest(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=100)]
    hex_code: str | None = None

    @field_validator("hex_code")
    @classmethod
    def hex_code_must_be_valid(cls, v: str | None) -> str | None:
        if v is not None and not re.match(r"^#[0-9A-Fa-f]{6}$", v):
            raise ValueError("hex_code must be in #RRGGBB format (e.g. '#FF5733')")
        return v


class CreateProductRequest(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=250)]
    category_id: uuid.UUID | None = None
    product_group_id: uuid.UUID | None = None
    product_type_id: uuid.UUID | None = None
    brand_id: uuid.UUID | None = None
    description: str | None = None
    image_url: Annotated[str | None, Field(max_length=500)] = None


class UpdateProductRequest(CreateProductRequest):
    pass


class CreateVariantRequest(BaseModel):
    size_id: uuid.UUID
    color_id: uuid.UUID
    mrp: Annotated[Decimal, Field(gt=0)]
    selling_price: Annotated[Decimal, Field(gt=0)]
    cost_price: Annotated[Decimal, Field(gt=0)]
    fabric: Annotated[str | None, Field(max_length=150)] = None
    image_url: Annotated[str | None, Field(max_length=500)] = None
    reorder_level: Annotated[int, Field(ge=0)] = 0


class UpdateVariantRequest(CreateVariantRequest):
    pass


class MasterDataImportResponse(BaseModel):
    entity_type: str
    created: int
    skipped: int
    errors: list[str] = []


# ── Response schemas ──────────────────────────────────────────────────────────

class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProductGroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProductTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class BrandResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SizeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ColorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    hex_code: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProductVariantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    product_id: uuid.UUID
    size_id: uuid.UUID
    color_id: uuid.UUID
    sku_code: str
    fabric: str | None
    image_url: str | None
    mrp: Decimal
    selling_price: Decimal
    cost_price: Decimal
    reorder_level: int
    status: str
    created_at: datetime
    updated_at: datetime

    @field_validator("image_url", mode="before")
    @classmethod
    def image_url_must_be_string_or_none(cls, v: object) -> str | None:
        if v is None or isinstance(v, str):
            return v
        return None


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    product_code: str
    name: str
    description: str | None
    image_url: str | None
    status: str
    category_id: uuid.UUID | None
    product_group_id: uuid.UUID | None
    product_type_id: uuid.UUID | None
    brand_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    variants: list[ProductVariantResponse] = Field(default_factory=list)

    @field_validator("variants", mode="before")
    @classmethod
    def variants_must_be_list(cls, v: object) -> list[ProductVariantResponse]:
        if isinstance(v, list):
            return v
        return []
