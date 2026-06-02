"""
Sales Pydantic schemas.

Validation rules
----------------
- quantity: gt=0
- selling_price: gt=0
- unit_cost: ge=0 (may be zero for gifted/promo items)
- tax_rate: ge=0, le=1 (fractional)
- discount_amount: ge=0
- payment amount: gt=0
- lines: min_length=1 (a bill must have at least one item)
- customer_id: optional (walk-in sales)
"""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.models.sales import SalePaymentMode


# ── Request schemas ───────────────────────────────────────────────────────────

class CreateCustomerRequest(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=250)]
    email: Annotated[str | None, Field(max_length=254)] = None
    phone: Annotated[str | None, Field(max_length=20)] = None
    address: str | None = None


class CreateSaleBillLineRequest(BaseModel):
    product_variant_id: uuid.UUID
    quantity: Annotated[Decimal, Field(gt=0)]
    selling_price: Annotated[Decimal, Field(gt=0)]
    tax_rate: Annotated[Decimal, Field(ge=0, le=1)] = Decimal("0")
    discount_amount: Annotated[Decimal, Field(ge=0)] = Decimal("0")


class CreateSalePaymentRequest(BaseModel):
    amount: Annotated[Decimal, Field(gt=0)]
    payment_mode: SalePaymentMode
    transaction_id: Annotated[str | None, Field(max_length=100)] = None
    notes: str | None = None


class CreateSaleBillRequest(BaseModel):
    location_id: uuid.UUID
    bin_id: uuid.UUID
    bill_date: date
    customer_id: uuid.UUID | None = None
    notes: str | None = None
    lines: Annotated[list[CreateSaleBillLineRequest], Field(min_length=1)]
    payment: CreateSalePaymentRequest


class SalesInvoiceImportResponse(BaseModel):
    imported: int
    skipped: int
    errors: list[str]
    invoices: list[str]


# ── Response schemas ──────────────────────────────────────────────────────────

class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    email: str | None
    phone: str | None
    address: str | None
    loyalty_points: int
    is_active: bool


class SaleBillLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    bill_id: uuid.UUID
    product_variant_id: uuid.UUID
    quantity: Decimal
    selling_price: Decimal
    unit_cost: Decimal
    tax_rate: Decimal
    discount_amount: Decimal
    total_line_amount: Decimal


class SalePaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    bill_id: uuid.UUID
    payment_date: date
    amount: Decimal
    payment_mode: str
    transaction_id: str | None
    notes: str | None


class SaleBillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    customer_id: uuid.UUID | None
    location_id: uuid.UUID
    bin_id: uuid.UUID
    invoice_number: str
    bill_date: date
    total_amount: Decimal
    tax_amount: Decimal
    total_discount: Decimal
    status: str
    notes: str | None
    lines: list[SaleBillLineResponse]
    payments: list[SalePaymentResponse]


class InvoiceMetadata(BaseModel):
    """Returned after PDF generation — client uses file_path to retrieve."""
    invoice_number: str
    file_path: str
    file_size_bytes: int
