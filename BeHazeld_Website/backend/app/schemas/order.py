from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CheckoutItemCreate(BaseModel):
    product_id: int
    # variant_id is required for the new schema — it identifies the exact
    # size/colour the customer selected and is used for stock decrement.
    # Set to None only for legacy/direct API calls without a variant.
    variant_id: int | None = None
    quantity: int = Field(gt=0, le=99)


class CheckoutCreate(BaseModel):
    customer_email: str = Field(min_length=3, max_length=255)
    customer_name: str = Field(min_length=2, max_length=160)
    shipping_address: str = Field(min_length=5, max_length=500)
    city: str = Field(min_length=2, max_length=120)
    state: str = Field(min_length=2, max_length=120)
    postal_code: str = Field(min_length=3, max_length=40)
    country: str = Field(min_length=2, max_length=80)
    items: list[CheckoutItemCreate] = Field(min_length=1)


class OrderItemRead(BaseModel):
    id: int
    product_id: int
    product_name: str
    product_slug: str
    variant_id: int | None
    color: str
    size: str
    unit_price: Decimal
    quantity: int
    line_total: Decimal

    model_config = ConfigDict(from_attributes=True)


class OrderRead(BaseModel):
    id: int
    customer_email: str
    customer_name: str
    shipping_address: str
    city: str
    state: str
    postal_code: str
    country: str
    status: str
    subtotal: Decimal
    shipping_total: Decimal
    total: Decimal
    created_at: datetime
    items: list[OrderItemRead]

    model_config = ConfigDict(from_attributes=True)
