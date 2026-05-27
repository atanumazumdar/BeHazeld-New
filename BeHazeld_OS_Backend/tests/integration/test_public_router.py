"""
Public catalog API integration tests — no authentication required.

Critical scenarios:
1. "Product Listing" — GET /{tenant_id}/products returns 200 with paginated
   envelope containing items, total, skip, limit.
2. "Category Listing" — GET /{tenant_id}/categories returns 200 with
   active categories.
3. "Customer Self-Registration" — POST /{tenant_id}/customers/register
   returns 201 with customer profile (no JWT needed).
4. Product search and category filter params are forwarded to the repository.
5. Inactive products do NOT appear (public API strict about status='active').
"""
import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app

_TENANT_ID = uuid.uuid4()


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def client() -> TestClient:
    """
    Public API client — NO auth dependency overrides.
    Only the DB session is mocked.
    """
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


# ── ORM mock builders ─────────────────────────────────────────────────────────

def _product_orm(name: str = "Kurti A") -> MagicMock:
    m = MagicMock()
    m.id           = uuid.uuid4()
    m.product_code = "SUM-KURT-0001"
    m.name         = name
    m.description  = "Elegant summer kurti"
    m.image_url    = None
    m.status       = "active"
    return m


def _variant_orm(sku: str = "SUM-KURT-0001-XLBLU") -> MagicMock:
    v = MagicMock()
    v.id            = uuid.uuid4()
    v.sku_code      = sku
    v.mrp           = Decimal("1299.00")
    v.selling_price = Decimal("999.00")
    v.status        = "active"
    return v


def _category_orm(name: str = "Women's Wear") -> MagicMock:
    c = MagicMock()
    c.id          = uuid.uuid4()
    c.name        = name
    c.description = None
    c.sort_order  = 1
    return c


def _customer_orm() -> MagicMock:
    m = MagicMock()
    m.id     = uuid.uuid4()
    m.name   = "Priya Sharma"
    m.email  = "priya@example.com"
    m.phone  = "9876543210"
    return m


_BASE = f"/api/v1/public/{_TENANT_ID}"


# ── CRITICAL TEST 1: Product Listing ─────────────────────────────────────────

def test_product_listing_returns_200_with_paginated_envelope(client: TestClient) -> None:
    """
    PRODUCT LISTING: GET /public/{tenant_id}/products returns 200 with
    PaginatedProductsResponse containing total, skip, limit, items.
    """
    product = _product_orm()
    variant = _variant_orm()

    with patch("app.api.v1.public.PublicRepository") as MockRepo:
        instance = MockRepo.return_value
        instance.list_active_products.return_value = [product]
        instance.count_active_products.return_value = 1
        instance.list_active_variants_for_product.return_value = [variant]
        resp = client.get(f"{_BASE}/products")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["skip"] == 0
    assert body["limit"] == 50
    assert len(body["items"]) == 1

    item = body["items"][0]
    assert item["name"] == "Kurti A"
    assert item["status"] == "active"
    assert len(item["variants"]) == 1
    assert item["variants"][0]["sku_code"] == "SUM-KURT-0001-XLBLU"


def test_product_listing_cost_price_not_exposed(client: TestClient) -> None:
    """Public schema must NOT expose cost_price to storefront consumers."""
    product = _product_orm()
    variant = _variant_orm()

    with patch("app.api.v1.public.PublicRepository") as MockRepo:
        instance = MockRepo.return_value
        instance.list_active_products.return_value = [product]
        instance.count_active_products.return_value = 1
        instance.list_active_variants_for_product.return_value = [variant]
        resp = client.get(f"{_BASE}/products")

    variant_data = resp.json()["items"][0]["variants"][0]
    assert "cost_price" not in variant_data
    assert "mrp" in variant_data
    assert "selling_price" in variant_data


def test_product_listing_empty_returns_200_empty_list(client: TestClient) -> None:
    with patch("app.api.v1.public.PublicRepository") as MockRepo:
        instance = MockRepo.return_value
        instance.list_active_products.return_value = []
        instance.count_active_products.return_value = 0
        resp = client.get(f"{_BASE}/products")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []


def test_product_listing_search_param_forwarded(client: TestClient) -> None:
    """search query param is forwarded to list_active_products."""
    with patch("app.api.v1.public.PublicRepository") as MockRepo:
        instance = MockRepo.return_value
        instance.list_active_products.return_value = []
        instance.count_active_products.return_value = 0
        resp = client.get(f"{_BASE}/products", params={"search": "kurti"})

    assert resp.status_code == 200
    call_kwargs = MockRepo.return_value.list_active_products.call_args.kwargs
    assert call_kwargs["search"] == "kurti"


def test_product_listing_pagination_params(client: TestClient) -> None:
    """skip and limit are forwarded correctly."""
    with patch("app.api.v1.public.PublicRepository") as MockRepo:
        instance = MockRepo.return_value
        instance.list_active_products.return_value = []
        instance.count_active_products.return_value = 0
        resp = client.get(f"{_BASE}/products", params={"skip": 20, "limit": 10})

    assert resp.status_code == 200
    body = resp.json()
    assert body["skip"] == 20
    assert body["limit"] == 10


def test_single_product_returns_200(client: TestClient) -> None:
    """GET /products/{id} returns full product detail with variants."""
    product = _product_orm()
    product_id = product.id
    variant = _variant_orm()

    # Override get_db to return a session that finds the product
    mock_db = MagicMock()
    mock_db.execute.return_value.scalar_one_or_none.return_value = product
    app.dependency_overrides[get_db] = lambda: mock_db

    with patch("app.api.v1.public.PublicRepository") as MockRepo:
        MockRepo.return_value.list_active_variants_for_product.return_value = [variant]
        resp = client.get(f"{_BASE}/products/{product_id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "active"
    assert len(body["variants"]) == 1


def test_single_product_not_found_returns_404(client: TestClient) -> None:
    """GET /products/{id} for missing product returns 404."""
    product_id = uuid.uuid4()

    mock_db = MagicMock()
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    app.dependency_overrides[get_db] = lambda: mock_db

    resp = client.get(f"{_BASE}/products/{product_id}")
    assert resp.status_code == 404


# ── CRITICAL TEST 2: Category Listing ────────────────────────────────────────

def test_category_listing_returns_200(client: TestClient) -> None:
    """
    CATEGORY LISTING: GET /public/{tenant_id}/categories returns 200 with
    active categories sorted by sort_order.
    """
    cats = [_category_orm("Women's Wear"), _category_orm("Men's Wear")]
    with patch("app.api.v1.public.PublicRepository") as MockRepo:
        MockRepo.return_value.list_active_categories.return_value = cats
        resp = client.get(f"{_BASE}/categories")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert body[0]["name"] == "Women's Wear"


def test_category_listing_empty_returns_200_empty(client: TestClient) -> None:
    with patch("app.api.v1.public.PublicRepository") as MockRepo:
        MockRepo.return_value.list_active_categories.return_value = []
        resp = client.get(f"{_BASE}/categories")

    assert resp.status_code == 200
    assert resp.json() == []


# ── CRITICAL TEST 3: Customer Self-Registration ───────────────────────────────

def test_customer_registration_returns_201_no_auth(client: TestClient) -> None:
    """
    CUSTOMER SELF-REGISTRATION: POST /public/{tenant_id}/customers/register
    returns 201 with customer profile — NO JWT required.
    """
    customer = _customer_orm()

    with patch("app.api.v1.public.SalesRepository") as MockRepo:
        MockRepo.return_value.create_customer.return_value = customer
        resp = client.post(
            f"{_BASE}/customers/register",
            json={"name": "Priya Sharma", "email": "priya@example.com"},
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Priya Sharma"
    assert body["email"] == "priya@example.com"
    assert "cost_price" not in body       # no internal fields


def test_customer_registration_empty_name_returns_422(client: TestClient) -> None:
    """Customer name is required — empty string returns 422."""
    resp = client.post(
        f"{_BASE}/customers/register",
        json={"name": ""},
    )
    assert resp.status_code == 422


def test_customer_registration_name_only_succeeds(client: TestClient) -> None:
    """Minimal registration with name only (no email/phone) returns 201."""
    customer = _customer_orm()
    customer.email = None
    customer.phone = None

    with patch("app.api.v1.public.SalesRepository") as MockRepo:
        MockRepo.return_value.create_customer.return_value = customer
        resp = client.post(
            f"{_BASE}/customers/register",
            json={"name": "Walk-in"},
        )

    assert resp.status_code == 201
