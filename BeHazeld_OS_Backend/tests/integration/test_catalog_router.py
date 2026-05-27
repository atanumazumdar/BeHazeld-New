"""
Catalog router integration tests.

DB is mocked via dependency_overrides; get_current_tenant is overridden with
a superuser context so permission checks pass. Service calls are patched at
the router module level to keep tests fast and focused on HTTP contracts.
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.deps import TenantContext, get_current_tenant
from app.db.session import get_db
from app.main import app

_TENANT_ID = uuid.uuid4()
_USER_ID = uuid.uuid4()
_NOW = datetime.now(timezone.utc)

# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def superuser_ctx() -> TenantContext:
    return TenantContext(
        tenant_id=_TENANT_ID,
        user_id=_USER_ID,
        permissions=["*"],
        is_superuser=True,
    )


@pytest.fixture
def client(superuser_ctx: TenantContext) -> TestClient:
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_tenant] = lambda: superuser_ctx
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


# ── helper builders ───────────────────────────────────────────────────────────

def _category_orm(name: str = "Tops") -> MagicMock:
    m = MagicMock()
    m.id = uuid.uuid4()
    m.tenant_id = _TENANT_ID
    m.name = name
    m.description = None
    m.sort_order = 0
    m.is_active = True
    m.created_at = _NOW
    m.updated_at = _NOW
    return m


def _product_orm(name: str = "Summer Kurti") -> MagicMock:
    m = MagicMock()
    m.id = uuid.uuid4()
    m.tenant_id = _TENANT_ID
    m.product_code = "SUM-KURT-0001"
    m.name = name
    m.description = None
    m.image_url = None
    m.status = "active"
    m.category_id = None
    m.product_group_id = None
    m.product_type_id = None
    m.brand_id = None
    m.created_at = _NOW
    m.updated_at = _NOW
    return m


def _variant_orm() -> MagicMock:
    m = MagicMock()
    m.id = uuid.uuid4()
    m.tenant_id = _TENANT_ID
    m.product_id = uuid.uuid4()
    m.size_id = uuid.uuid4()
    m.color_id = uuid.uuid4()
    m.sku_code = "SUM-KURT-0001-XLMID"
    m.fabric = None
    m.mrp = Decimal("500")
    m.selling_price = Decimal("400")
    m.cost_price = Decimal("250")
    m.reorder_level = 0
    m.status = "active"
    m.created_at = _NOW
    m.updated_at = _NOW
    return m


# ── GET /catalog/categories ───────────────────────────────────────────────────

def test_list_categories_returns_200(client: TestClient) -> None:
    with patch("app.api.v1.catalog.CatalogService") as MockSvc:
        MockSvc.return_value.list_categories.return_value = [_category_orm()]
        resp = client.get("/api/v1/catalog/categories")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert data[0]["name"] == "Tops"


# ── POST /catalog/categories ──────────────────────────────────────────────────

def test_create_category_returns_201(client: TestClient) -> None:
    with patch("app.api.v1.catalog.CatalogService") as MockSvc:
        MockSvc.return_value.create_category.return_value = _category_orm("Bottoms")
        resp = client.post("/api/v1/catalog/categories", json={"name": "Bottoms"})
    assert resp.status_code == 201
    assert resp.json()["name"] == "Bottoms"


def test_create_category_empty_name_returns_422(client: TestClient) -> None:
    resp = client.post("/api/v1/catalog/categories", json={"name": ""})
    assert resp.status_code == 422


def test_create_category_negative_sort_order_returns_422(client: TestClient) -> None:
    resp = client.post("/api/v1/catalog/categories", json={"name": "Tops", "sort_order": -1})
    assert resp.status_code == 422


# ── GET /catalog/products ─────────────────────────────────────────────────────

def test_list_products_returns_200(client: TestClient) -> None:
    with patch("app.api.v1.catalog.CatalogService") as MockSvc:
        MockSvc.return_value.list_products.return_value = [_product_orm()]
        resp = client.get("/api/v1/catalog/products")
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["product_code"] == "SUM-KURT-0001"


# ── POST /catalog/products ────────────────────────────────────────────────────

def test_create_product_returns_201(client: TestClient) -> None:
    with patch("app.api.v1.catalog.CatalogService") as MockSvc:
        MockSvc.return_value.create_product.return_value = _product_orm()
        resp = client.post("/api/v1/catalog/products", json={"name": "Summer Kurti"})
    assert resp.status_code == 201
    assert resp.json()["status"] == "active"


def test_create_product_empty_name_returns_422(client: TestClient) -> None:
    resp = client.post("/api/v1/catalog/products", json={"name": ""})
    assert resp.status_code == 422


def test_create_product_group_not_found_returns_404(client: TestClient) -> None:
    from app.core.exceptions import NotFoundError
    with patch("app.api.v1.catalog.CatalogService") as MockSvc:
        MockSvc.return_value.create_product.side_effect = NotFoundError("Group not found")
        resp = client.post(
            "/api/v1/catalog/products",
            json={"name": "Kurti", "product_group_id": str(uuid.uuid4())},
        )
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "NOT_FOUND"


# ── GET /catalog/products/{id} ────────────────────────────────────────────────

def test_get_product_returns_200(client: TestClient) -> None:
    product_id = uuid.uuid4()
    with patch("app.api.v1.catalog.CatalogService") as MockSvc:
        MockSvc.return_value.get_product.return_value = _product_orm()
        resp = client.get(f"/api/v1/catalog/products/{product_id}")
    assert resp.status_code == 200


def test_get_product_not_found_returns_404(client: TestClient) -> None:
    from app.core.exceptions import NotFoundError
    product_id = uuid.uuid4()
    with patch("app.api.v1.catalog.CatalogService") as MockSvc:
        MockSvc.return_value.get_product.side_effect = NotFoundError("Not found")
        resp = client.get(f"/api/v1/catalog/products/{product_id}")
    assert resp.status_code == 404


# ── POST /catalog/products/{id}/variants ──────────────────────────────────────

def test_create_variant_returns_201(client: TestClient) -> None:
    product_id = uuid.uuid4()
    with patch("app.api.v1.catalog.CatalogService") as MockSvc:
        MockSvc.return_value.create_variant.return_value = _variant_orm()
        resp = client.post(
            f"/api/v1/catalog/products/{product_id}/variants",
            json={
                "size_id": str(uuid.uuid4()),
                "color_id": str(uuid.uuid4()),
                "mrp": "500",
                "selling_price": "400",
                "cost_price": "250",
            },
        )
    assert resp.status_code == 201
    assert resp.json()["sku_code"] == "SUM-KURT-0001-XLMID"


def test_create_variant_zero_price_returns_422(client: TestClient) -> None:
    product_id = uuid.uuid4()
    resp = client.post(
        f"/api/v1/catalog/products/{product_id}/variants",
        json={
            "size_id": str(uuid.uuid4()),
            "color_id": str(uuid.uuid4()),
            "mrp": "0",
            "selling_price": "400",
            "cost_price": "250",
        },
    )
    assert resp.status_code == 422


# ── DELETE /catalog/products/{id} ─────────────────────────────────────────────

def test_delete_product_returns_200(client: TestClient) -> None:
    product_id = uuid.uuid4()
    deleted = _product_orm()
    deleted.status = "deleted"
    with patch("app.api.v1.catalog.CatalogService") as MockSvc:
        MockSvc.return_value.soft_delete_product.return_value = deleted
        resp = client.delete(f"/api/v1/catalog/products/{product_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"


# ── GET /catalog/products — search and filter params ─────────────────────────

def test_product_listing_search_param_forwarded_to_service(client: TestClient) -> None:
    """search query param is forwarded to CatalogService.list_products."""
    with patch("app.api.v1.catalog.CatalogService") as MockSvc:
        MockSvc.return_value.list_products.return_value = []
        resp = client.get("/api/v1/catalog/products", params={"search": "kurti"})
    assert resp.status_code == 200
    call_kwargs = MockSvc.return_value.list_products.call_args.kwargs
    assert call_kwargs["search"] == "kurti"


def test_product_listing_category_filter_forwarded(client: TestClient) -> None:
    """category_id query param is forwarded to CatalogService.list_products."""
    cat_id = uuid.uuid4()
    with patch("app.api.v1.catalog.CatalogService") as MockSvc:
        MockSvc.return_value.list_products.return_value = []
        resp = client.get("/api/v1/catalog/products", params={"category_id": str(cat_id)})
    assert resp.status_code == 200
    call_kwargs = MockSvc.return_value.list_products.call_args.kwargs
    assert call_kwargs["category_id"] == cat_id


def test_product_listing_status_param_forwarded(client: TestClient) -> None:
    """status=deleted returns deleted products."""
    with patch("app.api.v1.catalog.CatalogService") as MockSvc:
        MockSvc.return_value.list_products.return_value = []
        resp = client.get("/api/v1/catalog/products", params={"status": "deleted"})
    assert resp.status_code == 200
    call_kwargs = MockSvc.return_value.list_products.call_args.kwargs
    assert call_kwargs["status"] == "deleted"
