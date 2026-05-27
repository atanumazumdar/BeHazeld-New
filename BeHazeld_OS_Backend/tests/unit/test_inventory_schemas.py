"""Inventory schema validation tests — no DB required."""
from decimal import Decimal

import pytest
from pydantic import ValidationError


def test_create_bin_requires_name() -> None:
    from app.schemas.inventory import CreateBinRequest
    with pytest.raises(ValidationError):
        CreateBinRequest(name="")


def test_record_movement_quantity_must_be_positive() -> None:
    from app.schemas.inventory import RecordMovementRequest
    import uuid
    base = dict(
        product_variant_id=uuid.uuid4(),
        location_id=uuid.uuid4(),
        bin_id=uuid.uuid4(),
        movement_type="purchase_in",
        unit_cost=Decimal("100"),
    )
    with pytest.raises(ValidationError):
        RecordMovementRequest(**{**base, "quantity": Decimal("0")})
    with pytest.raises(ValidationError):
        RecordMovementRequest(**{**base, "quantity": Decimal("-5")})


def test_record_movement_unit_cost_must_be_non_negative() -> None:
    from app.schemas.inventory import RecordMovementRequest
    import uuid
    with pytest.raises(ValidationError):
        RecordMovementRequest(
            product_variant_id=uuid.uuid4(),
            location_id=uuid.uuid4(),
            bin_id=uuid.uuid4(),
            movement_type="purchase_in",
            quantity=Decimal("10"),
            unit_cost=Decimal("-1"),
        )


def test_record_movement_invalid_movement_type_rejected() -> None:
    from app.schemas.inventory import RecordMovementRequest
    import uuid
    with pytest.raises(ValidationError):
        RecordMovementRequest(
            product_variant_id=uuid.uuid4(),
            location_id=uuid.uuid4(),
            bin_id=uuid.uuid4(),
            movement_type="invalid_type",
            quantity=Decimal("10"),
            unit_cost=Decimal("100"),
        )


def test_record_movement_valid_inward() -> None:
    from app.schemas.inventory import RecordMovementRequest
    import uuid
    req = RecordMovementRequest(
        product_variant_id=uuid.uuid4(),
        location_id=uuid.uuid4(),
        bin_id=uuid.uuid4(),
        movement_type="purchase_in",
        quantity=Decimal("50"),
        unit_cost=Decimal("450.00"),
        batch_number="BATCH-001",
    )
    assert req.quantity == Decimal("50")
    assert req.movement_type == "purchase_in"


def test_stock_balance_response_from_orm() -> None:
    from app.schemas.inventory import StockBalanceResponse
    from unittest.mock import MagicMock, PropertyMock
    from decimal import Decimal
    import uuid
    m = MagicMock()
    m.id = uuid.uuid4()
    m.product_variant_id = uuid.uuid4()
    m.location_id = uuid.uuid4()
    m.bin_id = uuid.uuid4()
    m.quantity_on_hand = Decimal("100")
    m.quantity_reserved = Decimal("20")
    # quantity_available is a @property on the ORM model
    type(m).quantity_available = PropertyMock(return_value=Decimal("80"))
    r = StockBalanceResponse.model_validate(m)
    assert r.quantity_available == Decimal("80")
