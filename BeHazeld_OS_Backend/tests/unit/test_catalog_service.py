"""
CatalogService unit tests — all DB calls mocked.

Focus: product_code generation logic, SKU generation, FK validation.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import ConflictError, NotFoundError
from app.schemas.catalog import (
    CreateProductGroupRequest,
    CreateProductRequest,
    CreateVariantRequest,
)
from app.services.catalog_service import CatalogService


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_service():
    """Return a CatalogService with a fully mocked DB session."""
    db = MagicMock()
    svc = CatalogService(db)
    return svc, db


def _mock_group(name: str) -> MagicMock:
    g = MagicMock()
    g.name = name
    return g


def _mock_size(name: str) -> MagicMock:
    s = MagicMock()
    s.name = name
    return s


def _mock_color(name: str) -> MagicMock:
    c = MagicMock()
    c.name = name
    return c


def _mock_product(code: str) -> MagicMock:
    p = MagicMock()
    p.product_code = code
    return p


# ── product code generation ───────────────────────────────────────────────────

def test_create_product_uses_group_name_for_code() -> None:
    """When a product_group_id is given, group.name drives the code prefix."""
    svc, db = _make_service()
    tenant_id = uuid.uuid4()
    group_id = uuid.uuid4()

    svc.repo.count_products_by_tenant = MagicMock(return_value=0)
    svc.repo.get_product_group_by_id = MagicMock(return_value=_mock_group("Summer Collection"))
    created_product = MagicMock()
    svc.repo.create_product = MagicMock(return_value=created_product)

    req = CreateProductRequest(name="Kurti", product_group_id=group_id)
    svc.create_product(tenant_id, req)

    call_kwargs = svc.repo.create_product.call_args
    assert call_kwargs.kwargs["product_code"] == "SUM-KURT-0001"


def test_create_product_falls_back_to_product_name_when_no_group() -> None:
    """When product_group_id is None, product name is used for both group and name slots."""
    svc, db = _make_service()
    tenant_id = uuid.uuid4()

    svc.repo.count_products_by_tenant = MagicMock(return_value=5)
    created_product = MagicMock()
    svc.repo.create_product = MagicMock(return_value=created_product)

    req = CreateProductRequest(name="Jacket")
    svc.create_product(tenant_id, req)

    call_kwargs = svc.repo.create_product.call_args
    assert call_kwargs.kwargs["product_code"] == "JAC-JACK-0006"


def test_create_product_raises_if_group_not_found() -> None:
    """If product_group_id is given but not found, NotFoundError is raised."""
    svc, _ = _make_service()
    tenant_id = uuid.uuid4()

    svc.repo.count_products_by_tenant = MagicMock(return_value=0)
    svc.repo.get_product_group_by_id = MagicMock(return_value=None)
    svc.repo.create_product = MagicMock()

    req = CreateProductRequest(name="Kurti", product_group_id=uuid.uuid4())
    with pytest.raises(NotFoundError):
        svc.create_product(tenant_id, req)
    # create_product on repo must NOT have been called
    svc.repo.create_product.assert_not_called()


def test_create_product_sequence_increments_correctly() -> None:
    """Sequence = count + 1, so the 10th product has seq=10."""
    svc, _ = _make_service()
    tenant_id = uuid.uuid4()

    svc.repo.count_products_by_tenant = MagicMock(return_value=9)
    created = MagicMock()
    svc.repo.create_product = MagicMock(return_value=created)

    req = CreateProductRequest(name="Shirt")
    svc.create_product(tenant_id, req)

    code = svc.repo.create_product.call_args.kwargs["product_code"]
    assert code.endswith("-0010")


# ── variant / SKU generation ──────────────────────────────────────────────────

def test_create_variant_generates_correct_sku() -> None:
    """SKU = product_code + size[:2] + color[:3], all upper, no spaces."""
    svc, _ = _make_service()
    tenant_id = uuid.uuid4()
    product_id = uuid.uuid4()

    svc.repo.get_product_by_id = MagicMock(return_value=_mock_product("SUM-KURT-0001"))
    svc.repo.get_size_by_id = MagicMock(return_value=_mock_size("XL"))
    svc.repo.get_color_by_id = MagicMock(return_value=_mock_color("Midnight Blue"))
    created_variant = MagicMock()
    svc.repo.create_variant = MagicMock(return_value=created_variant)

    req = CreateVariantRequest(
        size_id=uuid.uuid4(),
        color_id=uuid.uuid4(),
        mrp=Decimal("500"),
        selling_price=Decimal("400"),
        cost_price=Decimal("250"),
    )
    svc.create_variant(tenant_id, product_id, req)

    sku = svc.repo.create_variant.call_args.kwargs["sku_code"]
    assert sku == "SUM-KURT-0001-XLMID"


def test_create_variant_raises_if_size_not_found() -> None:
    svc, _ = _make_service()
    tenant_id = uuid.uuid4()
    product_id = uuid.uuid4()

    svc.repo.get_product_by_id = MagicMock(return_value=_mock_product("X-Y-0001"))
    svc.repo.get_size_by_id = MagicMock(return_value=None)
    svc.repo.create_variant = MagicMock()

    req = CreateVariantRequest(
        size_id=uuid.uuid4(),
        color_id=uuid.uuid4(),
        mrp=Decimal("100"),
        selling_price=Decimal("80"),
        cost_price=Decimal("50"),
    )
    with pytest.raises(NotFoundError):
        svc.create_variant(tenant_id, product_id, req)
    svc.repo.create_variant.assert_not_called()


def test_create_variant_raises_if_color_not_found() -> None:
    svc, _ = _make_service()
    tenant_id = uuid.uuid4()
    product_id = uuid.uuid4()

    svc.repo.get_product_by_id = MagicMock(return_value=_mock_product("X-Y-0001"))
    svc.repo.get_size_by_id = MagicMock(return_value=_mock_size("M"))
    svc.repo.get_color_by_id = MagicMock(return_value=None)
    svc.repo.create_variant = MagicMock()

    req = CreateVariantRequest(
        size_id=uuid.uuid4(),
        color_id=uuid.uuid4(),
        mrp=Decimal("100"),
        selling_price=Decimal("80"),
        cost_price=Decimal("50"),
    )
    with pytest.raises(NotFoundError):
        svc.create_variant(tenant_id, product_id, req)
    svc.repo.create_variant.assert_not_called()


def test_create_variant_propagates_conflict_from_repo() -> None:
    """Duplicate SKU → ConflictError bubbles up from the repo."""
    svc, _ = _make_service()
    tenant_id = uuid.uuid4()
    product_id = uuid.uuid4()

    svc.repo.get_product_by_id = MagicMock(return_value=_mock_product("X-Y-0001"))
    svc.repo.get_size_by_id = MagicMock(return_value=_mock_size("S"))
    svc.repo.get_color_by_id = MagicMock(return_value=_mock_color("Red"))
    svc.repo.create_variant = MagicMock(side_effect=ConflictError("SKU exists"))

    req = CreateVariantRequest(
        size_id=uuid.uuid4(),
        color_id=uuid.uuid4(),
        mrp=Decimal("100"),
        selling_price=Decimal("80"),
        cost_price=Decimal("50"),
    )
    with pytest.raises(ConflictError):
        svc.create_variant(tenant_id, product_id, req)


# ── read pass-throughs ────────────────────────────────────────────────────────

def test_list_products_delegates_to_repo() -> None:
    svc, _ = _make_service()
    tenant_id = uuid.uuid4()
    fake_products = [MagicMock(), MagicMock()]
    svc.repo.list_products = MagicMock(return_value=fake_products)

    result = svc.list_products(tenant_id)

    svc.repo.list_products.assert_called_once_with(
        tenant_id,
        status="active",
        skip=0,
        limit=50,
        search=None,
        category_id=None,
        brand_id=None,
    )
    assert result is fake_products
