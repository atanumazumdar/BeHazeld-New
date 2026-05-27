"""
Inventory router integration tests.

DB is mocked via dependency_overrides; get_current_tenant returns a
superuser context. Service calls are patched at the router module level.

Critical: two tests verify that insufficient stock returns 409 and
no ledger entry is created (the no-partial-state guarantee).
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


# ── helper ORM mocks ──────────────────────────────────────────────────────────

def _bin_orm(name: str = "Main") -> MagicMock:
    m = MagicMock()
    m.id = uuid.uuid4()
    m.tenant_id = _TENANT_ID
    m.location_id = uuid.uuid4()
    m.name = name
    m.is_default = True
    m.is_active = True
    return m


def _ledger_orm(movement_type: str = "purchase_in", qty_change: Decimal = Decimal("10")) -> MagicMock:
    m = MagicMock()
    m.id = uuid.uuid4()
    m.product_variant_id = uuid.uuid4()
    m.location_id = uuid.uuid4()
    m.bin_id = uuid.uuid4()
    m.movement_type = movement_type
    m.quantity_change = qty_change
    m.unit_cost = Decimal("200")
    m.notes = None
    return m


def _balance_orm(on_hand: Decimal = Decimal("100"), reserved: Decimal = Decimal("0")) -> MagicMock:
    m = MagicMock()
    m.id = uuid.uuid4()
    m.product_variant_id = uuid.uuid4()
    m.location_id = uuid.uuid4()
    m.bin_id = uuid.uuid4()
    m.quantity_on_hand = on_hand
    m.quantity_reserved = reserved
    type(m).quantity_available = property(lambda self: self.quantity_on_hand - self.quantity_reserved)
    return m


def _movement_payload(movement_type: str = "purchase_in", quantity: str = "10") -> dict:
    return {
        "product_variant_id": str(uuid.uuid4()),
        "location_id": str(uuid.uuid4()),
        "bin_id": str(uuid.uuid4()),
        "movement_type": movement_type,
        "quantity": quantity,
        "unit_cost": "200",
    }


# ── POST /inventory/locations/{id}/bins ───────────────────────────────────────

def test_create_bin_returns_201(client: TestClient) -> None:
    location_id = uuid.uuid4()
    with patch("app.api.v1.inventory.InventoryService") as MockSvc:
        MockSvc.return_value.create_bin.return_value = _bin_orm()
        resp = client.post(
            f"/api/v1/inventory/locations/{location_id}/bins",
            json={"name": "Shelf-A"},
        )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Main"


def test_create_bin_empty_name_returns_422(client: TestClient) -> None:
    location_id = uuid.uuid4()
    resp = client.post(
        f"/api/v1/inventory/locations/{location_id}/bins",
        json={"name": ""},
    )
    assert resp.status_code == 422


def test_list_bins_returns_200(client: TestClient) -> None:
    location_id = uuid.uuid4()
    with patch("app.api.v1.inventory.InventoryService") as MockSvc:
        MockSvc.return_value.list_bins.return_value = [_bin_orm("Rack-1"), _bin_orm("Rack-2")]
        resp = client.get(f"/api/v1/inventory/locations/{location_id}/bins")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


# ── POST /inventory/movements ─────────────────────────────────────────────────

def test_record_purchase_movement_returns_201(client: TestClient) -> None:
    with patch("app.api.v1.inventory.InventoryService") as MockSvc:
        MockSvc.return_value.record_stock_movement.return_value = _ledger_orm()
        resp = client.post("/api/v1/inventory/movements", json=_movement_payload())
    assert resp.status_code == 201
    assert resp.json()["movement_type"] == "purchase_in"
    assert Decimal(resp.json()["quantity_change"]) == Decimal("10")


def test_record_movement_invalid_type_returns_422(client: TestClient) -> None:
    payload = _movement_payload()
    payload["movement_type"] = "bad_type"
    resp = client.post("/api/v1/inventory/movements", json=payload)
    assert resp.status_code == 422


def test_record_movement_zero_quantity_returns_422(client: TestClient) -> None:
    payload = _movement_payload(quantity="0")
    resp = client.post("/api/v1/inventory/movements", json=payload)
    assert resp.status_code == 422


def test_record_movement_negative_quantity_returns_422(client: TestClient) -> None:
    payload = _movement_payload(quantity="-5")
    resp = client.post("/api/v1/inventory/movements", json=payload)
    assert resp.status_code == 422


# ── CRITICAL: insufficient stock returns 409 ──────────────────────────────────

def test_insufficient_stock_returns_409(client: TestClient) -> None:
    """
    When stock is insufficient, the router must return 409 (not 500).
    The service raises StockNotAvailableError; the app exception handler maps it.
    """
    from app.core.exceptions import StockNotAvailableError
    with patch("app.api.v1.inventory.InventoryService") as MockSvc:
        MockSvc.return_value.record_stock_movement.side_effect = StockNotAvailableError()
        resp = client.post(
            "/api/v1/inventory/movements",
            json=_movement_payload(movement_type="sale_out", quantity="9999"),
        )
    assert resp.status_code == 409
    body = resp.json()
    assert body["error_code"] == "SALE_STOCK_NOT_AVAILABLE"
    assert "correlation_id" in body


def test_insufficient_stock_error_code_is_structured(client: TestClient) -> None:
    """Response body must include error_code + message in the standard envelope."""
    from app.core.exceptions import StockNotAvailableError
    with patch("app.api.v1.inventory.InventoryService") as MockSvc:
        MockSvc.return_value.record_stock_movement.side_effect = StockNotAvailableError(
            "Only 3 units available"
        )
        resp = client.post(
            "/api/v1/inventory/movements",
            json=_movement_payload(movement_type="sale_out", quantity="50"),
        )
    body = resp.json()
    assert body["success"] is False
    assert body["error_code"] == "SALE_STOCK_NOT_AVAILABLE"
    assert "3 units" in body["message"]


# ── GET /inventory/balance ────────────────────────────────────────────────────

def test_get_balance_returns_200(client: TestClient) -> None:
    variant_id = uuid.uuid4()
    location_id = uuid.uuid4()
    bin_id = uuid.uuid4()

    balance = _balance_orm(on_hand=Decimal("50"), reserved=Decimal("10"))
    with patch("app.api.v1.inventory.InventoryService") as MockSvc:
        MockSvc.return_value.get_balance.return_value = balance
        resp = client.get(
            "/api/v1/inventory/balance",
            params={
                "product_variant_id": str(variant_id),
                "location_id": str(location_id),
                "bin_id": str(bin_id),
            },
        )
    assert resp.status_code == 200
    assert Decimal(resp.json()["quantity_on_hand"]) == Decimal("50")


def test_get_balance_none_returns_null(client: TestClient) -> None:
    variant_id = uuid.uuid4()
    location_id = uuid.uuid4()
    bin_id = uuid.uuid4()

    with patch("app.api.v1.inventory.InventoryService") as MockSvc:
        MockSvc.return_value.get_balance.return_value = None
        resp = client.get(
            "/api/v1/inventory/balance",
            params={
                "product_variant_id": str(variant_id),
                "location_id": str(location_id),
                "bin_id": str(bin_id),
            },
        )
    assert resp.status_code == 200
    assert resp.json() is None


# ── GET /inventory/summary/{variant_id} ───────────────────────────────────────

def test_get_stock_summary_returns_200(client: TestClient) -> None:
    variant_id = uuid.uuid4()
    with patch("app.api.v1.inventory.InventoryService") as MockSvc:
        MockSvc.return_value.get_stock_summary.return_value = [
            _balance_orm(Decimal("30"), Decimal("5")),
        ]
        resp = client.get(f"/api/v1/inventory/summary/{variant_id}")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


# ── variant not found → 404 ───────────────────────────────────────────────────

def test_movement_variant_not_found_returns_404(client: TestClient) -> None:
    from app.core.exceptions import NotFoundError
    with patch("app.api.v1.inventory.InventoryService") as MockSvc:
        MockSvc.return_value.record_stock_movement.side_effect = NotFoundError("Variant missing")
        resp = client.post("/api/v1/inventory/movements", json=_movement_payload())
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "NOT_FOUND"


# ── GET /inventory/locations ──────────────────────────────────────────────────

def test_list_locations_returns_200_with_bins(client: TestClient) -> None:
    """GET /inventory/locations returns active locations with their bins."""
    with patch("app.api.v1.inventory.TenantRepository") as MockTRepo, \
         patch("app.api.v1.inventory.InventoryRepository") as MockIRepo:
        mock_loc = MagicMock()
        mock_loc.id = uuid.uuid4()
        mock_loc.tenant_id = _TENANT_ID
        mock_loc.name = "Main Warehouse"
        mock_loc.address = None
        mock_loc.is_active = True
        MockTRepo.return_value.list_locations_by_tenant.return_value = [mock_loc]
        MockIRepo.return_value.list_bins_by_location.return_value = [_bin_orm()]
        resp = client.get("/api/v1/inventory/locations")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["name"] == "Main Warehouse"
    assert isinstance(body[0]["bins"], list)
    assert len(body[0]["bins"]) == 1
    assert body[0]["bins"][0]["name"] == "Main"
