"""Sales schema validation tests — no DB required."""
import uuid
from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.sales import SalePaymentMode
from app.schemas.sales import (
    CreateCustomerRequest,
    CreateSaleBillLineRequest,
    CreateSaleBillRequest,
    CreateSalePaymentRequest,
)


def _payment(**kw):
    return CreateSalePaymentRequest(
        amount=kw.get("amount", Decimal("100")),
        payment_mode=kw.get("payment_mode", SalePaymentMode.CASH),
    )


def _line(**kw):
    return CreateSaleBillLineRequest(
        product_variant_id=uuid.uuid4(),
        quantity=kw.get("quantity", Decimal("1")),
        selling_price=kw.get("selling_price", Decimal("100")),
        tax_rate=kw.get("tax_rate", Decimal("0")),
        discount_amount=kw.get("discount_amount", Decimal("0")),
    )


def test_customer_name_required() -> None:
    with pytest.raises(ValidationError):
        CreateCustomerRequest(name="")


def test_line_quantity_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        _line(quantity=Decimal("0"))
    with pytest.raises(ValidationError):
        _line(quantity=Decimal("-1"))


def test_line_selling_price_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        _line(selling_price=Decimal("0"))


def test_line_tax_rate_bounds() -> None:
    with pytest.raises(ValidationError):
        _line(tax_rate=Decimal("-0.01"))
    with pytest.raises(ValidationError):
        _line(tax_rate=Decimal("1.01"))
    # Boundary values must pass
    _line(tax_rate=Decimal("0"))
    _line(tax_rate=Decimal("1"))


def test_line_discount_must_be_non_negative() -> None:
    with pytest.raises(ValidationError):
        _line(discount_amount=Decimal("-1"))


def test_sale_bill_requires_at_least_one_line() -> None:
    with pytest.raises(ValidationError):
        CreateSaleBillRequest(
            location_id=uuid.uuid4(),
            bin_id=uuid.uuid4(),
            bill_date=date(2026, 5, 25),
            lines=[],
            payment=_payment(),
        )


def test_payment_amount_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        _payment(amount=Decimal("0"))


def test_payment_invalid_mode_rejected() -> None:
    with pytest.raises(ValidationError):
        _payment(payment_mode="bitcoin")


def test_valid_sale_bill_accepted() -> None:
    req = CreateSaleBillRequest(
        location_id=uuid.uuid4(),
        bin_id=uuid.uuid4(),
        bill_date=date(2026, 5, 25),
        lines=[_line(), _line()],
        payment=_payment(),
    )
    assert len(req.lines) == 2


def test_walk_in_sale_no_customer_id() -> None:
    req = CreateSaleBillRequest(
        location_id=uuid.uuid4(),
        bin_id=uuid.uuid4(),
        bill_date=date(2026, 5, 25),
        lines=[_line()],
        payment=_payment(),
    )
    assert req.customer_id is None
