"""Catalog schema validation tests — no DB required."""
from decimal import Decimal

import pytest
from pydantic import ValidationError


def test_create_category_requires_name() -> None:
    from app.schemas.catalog import CreateCategoryRequest
    with pytest.raises(ValidationError):
        CreateCategoryRequest(name="")


def test_create_category_sort_order_must_be_non_negative() -> None:
    from app.schemas.catalog import CreateCategoryRequest
    with pytest.raises(ValidationError):
        CreateCategoryRequest(name="Tops", sort_order=-1)


def test_create_color_rejects_invalid_hex() -> None:
    from app.schemas.catalog import CreateColorRequest
    with pytest.raises(ValidationError):
        CreateColorRequest(name="Red", hex_code="red")
    with pytest.raises(ValidationError):
        CreateColorRequest(name="Red", hex_code="#GGG")


def test_create_color_accepts_valid_hex() -> None:
    from app.schemas.catalog import CreateColorRequest
    c = CreateColorRequest(name="Midnight Blue", hex_code="#003153")
    assert c.hex_code == "#003153"


def test_create_color_accepts_none_hex() -> None:
    from app.schemas.catalog import CreateColorRequest
    c = CreateColorRequest(name="Natural")
    assert c.hex_code is None


def test_create_variant_prices_must_be_positive() -> None:
    from app.schemas.catalog import CreateVariantRequest
    import uuid
    base = dict(size_id=uuid.uuid4(), color_id=uuid.uuid4(),
                mrp=Decimal("100"), selling_price=Decimal("80"), cost_price=Decimal("50"))
    with pytest.raises(ValidationError):
        CreateVariantRequest(**{**base, "mrp": Decimal("0")})
    with pytest.raises(ValidationError):
        CreateVariantRequest(**{**base, "selling_price": Decimal("-1")})
    with pytest.raises(ValidationError):
        CreateVariantRequest(**{**base, "cost_price": Decimal("0")})


def test_create_variant_reorder_level_non_negative() -> None:
    from app.schemas.catalog import CreateVariantRequest
    import uuid
    with pytest.raises(ValidationError):
        CreateVariantRequest(
            size_id=uuid.uuid4(), color_id=uuid.uuid4(),
            mrp=Decimal("100"), selling_price=Decimal("80"), cost_price=Decimal("50"),
            reorder_level=-1,
        )


def test_product_response_from_orm() -> None:
    from app.schemas.catalog import ProductResponse
    from unittest.mock import MagicMock
    from datetime import datetime, timezone
    import uuid
    m = MagicMock()
    m.id = uuid.uuid4()
    m.tenant_id = uuid.uuid4()
    m.product_code = "SUM-KURT-0001"
    m.name = "Summer Kurti"
    m.description = None
    m.image_url = None
    m.status = "active"
    m.category_id = None
    m.product_group_id = None
    m.product_type_id = None
    m.brand_id = None
    m.created_at = datetime.now(timezone.utc)
    m.updated_at = datetime.now(timezone.utc)
    r = ProductResponse.model_validate(m)
    assert r.product_code == "SUM-KURT-0001"
    assert r.status == "active"
