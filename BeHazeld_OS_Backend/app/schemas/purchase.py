"""
Purchase Pydantic schemas — request validation and response serialization.

Validation rules
----------------
- name fields: min_length=1
- quantity: gt=0 (positive units only)
- unit_cost: ge=0 (zero allowed for sample / gift items)
- tax_rate: ge=0, le=1 (fractional: 0.18 = 18 %)
- amount (payment): gt=0
- bill_date / payment_date: ISO date string (YYYY-MM-DD) — validated as str,
  PostgreSQL DATE columns accept this ISO format.
"""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.models.purchase import BillStatus, PaymentMode


# ── Request schemas ───────────────────────────────────────────────────────────

class CreateVendorRequest(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=250)]
    gstin: Annotated[str | None, Field(max_length=20)] = None
    address: str | None = None
    contact_name: Annotated[str | None, Field(max_length=150)] = None
    contact_phone: Annotated[str | None, Field(max_length=20)] = None
    contact_email: Annotated[str | None, Field(max_length=254)] = None


class CreateTransporterRequest(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=250)]
    vehicle_no: Annotated[str | None, Field(max_length=50)] = None
    contact_phone: Annotated[str | None, Field(max_length=20)] = None


class CreatePurchaseBillLineRequest(BaseModel):
    product_variant_id: uuid.UUID
    quantity: Annotated[Decimal, Field(gt=0)]
    unit_cost: Annotated[Decimal, Field(ge=0)]
    # The service enforces 0% before 2026-09-01 and 5% from that date onward.
    tax_rate: Annotated[Decimal, Field(ge=0, le=1)] = Decimal("0")
    batch_number: Annotated[str | None, Field(max_length=100)] = None


class CreatePurchaseBillRequest(BaseModel):
    vendor_id: uuid.UUID
    location_id: uuid.UUID
    bin_id: uuid.UUID
    bill_number: Annotated[str, Field(min_length=1, max_length=100)]
    bill_date: date
    transporter_id: uuid.UUID | None = None
    notes: str | None = None
    lines: Annotated[list[CreatePurchaseBillLineRequest], Field(min_length=1)]


class RecordVendorPaymentRequest(BaseModel):
    bill_id: uuid.UUID
    payment_date: date
    amount: Annotated[Decimal, Field(gt=0)]
    payment_mode: PaymentMode
    reference_number: Annotated[str | None, Field(max_length=100)] = None
    notes: str | None = None


# ── Response schemas ──────────────────────────────────────────────────────────

class VendorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    gstin: str | None
    address: str | None
    contact_name: str | None
    contact_phone: str | None
    contact_email: str | None
    is_active: bool


class TransporterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    vehicle_no: str | None
    contact_phone: str | None
    is_active: bool


class PurchaseBillLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    bill_id: uuid.UUID
    product_variant_id: uuid.UUID
    quantity: Decimal
    unit_cost: Decimal
    tax_rate: Decimal
    total_line_amount: Decimal


class PurchaseBillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    vendor_id: uuid.UUID
    transporter_id: uuid.UUID | None
    location_id: uuid.UUID
    bin_id: uuid.UUID
    bill_number: str
    bill_date: date
    total_amount: Decimal
    tax_amount: Decimal
    status: str
    notes: str | None
    lines: list[PurchaseBillLineResponse]


class VendorPaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    bill_id: uuid.UUID
    payment_date: date
    amount: Decimal
    payment_mode: str
    reference_number: str | None
    notes: str | None
