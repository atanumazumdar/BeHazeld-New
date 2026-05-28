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

def test_create_product_generates_initials_code() -> None:
    """Product code is the first letter of each product-name word."""
    svc, db = _make_service()
    tenant_id = uuid.uuid4()
    group_id = uuid.uuid4()

    svc.repo.count_products_by_tenant = MagicMock(return_value=0)
    svc.repo.get_product_group_by_id = MagicMock(return_value=_mock_group("Summer Collection"))
    created_product = MagicMock()
    svc.repo.create_product = MagicMock(return_value=created_product)

    req = CreateProductRequest(name="Power Edit Georgette Kurti", product_group_id=group_id)
    svc.create_product(tenant_id, req)

    call_kwargs = svc.repo.create_product.call_args
    assert call_kwargs.kwargs["product_code"] == "PEGK"


def test_create_product_code_does_not_require_group() -> None:
    """Product code generation only needs the product name."""
    svc, db = _make_service()
    tenant_id = uuid.uuid4()

    svc.repo.count_products_by_tenant = MagicMock(return_value=5)
    created_product = MagicMock()
    svc.repo.create_product = MagicMock(return_value=created_product)

    req = CreateProductRequest(name="Jacket")
    svc.create_product(tenant_id, req)

    call_kwargs = svc.repo.create_product.call_args
    assert call_kwargs.kwargs["product_code"] == "J"


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


def test_import_master_data_csv_creates_categories() -> None:
    svc, db = _make_service()
    tenant_id = uuid.uuid4()
    db.scalars.return_value = []
    svc.repo.create_category = MagicMock()

    result = svc.import_master_data_csv(
        tenant_id,
        "categories",
        b"name,description,sort_order\nDresses,All dresses,1\nTops,,2\n",
    )

    assert result.created == 2
    assert result.skipped == 0
    assert result.errors == []
    assert svc.repo.create_category.call_count == 2
    assert svc.repo.create_category.call_args_list[0].kwargs["name"] == "Dresses"
    assert svc.repo.create_category.call_args_list[0].kwargs["sort_order"] == 1
    db.commit.assert_called_once()


def test_import_master_data_csv_skips_existing_names() -> None:
    svc, db = _make_service()
    tenant_id = uuid.uuid4()
    db.scalars.return_value = ["Black"]
    svc.repo.create_color = MagicMock()

    result = svc.import_master_data_csv(
        tenant_id,
        "colors",
        b"name,hex_code\nBlack,#000000\nRose,#E11D48\n",
    )

    assert result.created == 1
    assert result.skipped == 1
    assert result.errors == []
    svc.repo.create_color.assert_called_once()
    assert svc.repo.create_color.call_args.kwargs["name"] == "Rose"


def test_import_master_data_csv_accepts_quoted_whole_rows() -> None:
    svc, db = _make_service()
    tenant_id = uuid.uuid4()
    db.scalars.return_value = []
    svc.repo.create_product_group = MagicMock()

    result = svc.import_master_data_csv(
        tenant_id,
        "product-groups",
        b'"name,description"\n"Accessories,To Compliment U"\n',
    )

    assert result.created == 1
    assert result.errors == []
    svc.repo.create_product_group.assert_called_once_with(
        tenant_id=tenant_id,
        name="Accessories",
        description="To Compliment U",
    )


def test_import_master_data_csv_accepts_tab_delimited_exports() -> None:
    svc, db = _make_service()
    tenant_id = uuid.uuid4()
    db.scalars.return_value = []
    svc.repo.create_category = MagicMock()

    result = svc.import_master_data_csv(
        tenant_id,
        "categories",
        b"name\tdescription\tsort_order\nDresses\tAll dresses\t1\nTops\t\t2\n",
    )

    assert result.created == 2
    assert result.errors == []
    assert svc.repo.create_category.call_args_list[0].kwargs["name"] == "Dresses"
    assert svc.repo.create_category.call_args_list[0].kwargs["description"] == "All dresses"
    assert svc.repo.create_category.call_args_list[0].kwargs["sort_order"] == 1


def test_create_product_sequence_does_not_change_initials_code() -> None:
    """The legacy sequence argument is ignored by the initials-based code."""
    svc, _ = _make_service()
    tenant_id = uuid.uuid4()

    svc.repo.count_products_by_tenant = MagicMock(return_value=9)
    created = MagicMock()
    svc.repo.create_product = MagicMock(return_value=created)

    req = CreateProductRequest(name="Shirt")
    svc.create_product(tenant_id, req)

    code = svc.repo.create_product.call_args.kwargs["product_code"]
    assert code == "S"


# ── variant / SKU generation ──────────────────────────────────────────────────

def test_create_variant_generates_correct_sku() -> None:
    """SKU = product code + first 3 color letters + size."""
    svc, _ = _make_service()
    tenant_id = uuid.uuid4()
    product_id = uuid.uuid4()

    svc.repo.get_product_by_id = MagicMock(return_value=_mock_product("PEGK"))
    svc.repo.get_size_by_id = MagicMock(return_value=_mock_size("42"))
    svc.repo.get_color_by_id = MagicMock(return_value=_mock_color("Peach"))
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
    assert sku == "PEGK-PCH-42"


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
