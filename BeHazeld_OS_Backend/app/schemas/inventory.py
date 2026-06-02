"""
Inventory Pydantic schemas — request validation and response serialization.

Validation rules
----------------
- quantity: gt=0 (always positive; the service derives the sign from movement_type)
- unit_cost: ge=0 (zero is valid for adjustments and opening stock)
- movement_type: must be a valid MovementType string value
- bin name: min_length=1
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.models.inventory import MovementType


# ── Request schemas ───────────────────────────────────────────────────────────

class CreateBinRequest(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=100)]
    is_default: bool = False


class InventoryLocationImportResponse(BaseModel):
    created_locations: int
    created_bins: int
    skipped: int
    errors: list[str]


class BulkOpeningStockResponse(BaseModel):
    created: int
    skipped: int
    location_id: uuid.UUID
    location_name: str
    bin_id: uuid.UUID
    bin_name: str


class RecordMovementRequest(BaseModel):
    product_variant_id: uuid.UUID
    location_id: uuid.UUID
    bin_id: uuid.UUID
    movement_type: MovementType          # validated against the StrEnum
    quantity: Annotated[Decimal, Field(gt=0)]       # always positive; sign derived by service
    unit_cost: Annotated[Decimal, Field(ge=0)]      # zero valid for adjustments / opening stock
    batch_number: Annotated[str | None, Field(max_length=100)] = None
    notes: str | None = None


# ── Response schemas ──────────────────────────────────────────────────────────

class BinResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    location_id: uuid.UUID
    name: str
    is_default: bool
    is_active: bool


class StockMovementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_variant_id: uuid.UUID
    location_id: uuid.UUID
    bin_id: uuid.UUID
    movement_type: str
    quantity_change: Decimal
    unit_cost: Decimal
    notes: str | None


class StockBalanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_variant_id: uuid.UUID
    location_id: uuid.UUID
    bin_id: uuid.UUID
    quantity_on_hand: Decimal
    quantity_reserved: Decimal
    quantity_available: Decimal          # exposed from @property on ORM model


class LocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    address: str | None
    is_active: bool
    bins: list[BinResponse] = []
