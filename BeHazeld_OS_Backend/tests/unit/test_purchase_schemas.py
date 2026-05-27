"""Purchase schema validation tests — no DB required."""
import uuid
from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.purchase import (
    CreatePurchaseBillLineRequest,
    CreatePurchaseBillRequest,
    CreateVendorRequest,
    RecordVendorPaymentRequest,
)


def test_vendor_name_required() -> None:
    with pytest.raises(ValidationError):
        CreateVendorRequest(name="")


def test_bill_line_quantity_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        CreatePurchaseBillLineRequest(
            product_variant_id=uuid.uuid4(),
            quantity=Decimal("0"),
            unit_cost=Decimal("100"),
        )


def test_bill_line_unit_cost_zero_allowed() -> None:
    line = CreatePurchaseBillLineRequest(
        product_variant_id=uuid.uuid4(),
        quantity=Decimal("5"),
        unit_cost=Decimal("0"),
    )
    assert line.unit_cost == Decimal("0")


def test_bill_line_tax_rate_must_be_between_0_and_1() -> None:
    with pytest.raises(ValidationError):
        CreatePurchaseBillLineRequest(
            product_variant_id=uuid.uuid4(),
            quantity=Decimal("1"),
            unit_cost=Decimal("100"),
            tax_rate=Decimal("1.5"),  # > 1
        )


def test_bill_must_have_at_least_one_line() -> None:
    with pytest.raises(ValidationError):
        CreatePurchaseBillRequest(
            vendor_id=uuid.uuid4(),
            location_id=uuid.uuid4(),
            bin_id=uuid.uuid4(),
            bill_number="INV-001",
            bill_date=date(2026, 5, 25),
            lines=[],   # empty
        )


def test_payment_amount_must_be_positive() -> None:
    from app.models.purchase import PaymentMode
    with pytest.raises(ValidationError):
        RecordVendorPaymentRequest(
            bill_id=uuid.uuid4(),
            payment_date=date(2026, 5, 25),
            amount=Decimal("0"),
            payment_mode=PaymentMode.CASH,
        )


def test_payment_invalid_mode_rejected() -> None:
    with pytest.raises(ValidationError):
        RecordVendorPaymentRequest(
            bill_id=uuid.uuid4(),
            payment_date=date(2026, 5, 25),
            amount=Decimal("500"),
            payment_mode="bitcoin",  # invalid
        )
