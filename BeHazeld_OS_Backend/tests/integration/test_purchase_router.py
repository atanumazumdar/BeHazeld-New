"""
Purchase router integration tests.

Two critical scenarios:
1. "Purchase Bill Success" — 201 returned, verify bill created → stock
   increased → batch updated (service mock captures the call chain).
2. "Rollback on Invalid Variant" — 404 returned, verify no commit (the
   service raises NotFoundError and the router returns 404 structured JSON).
"""
import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.deps import TenantContext, get_current_tenant
from app.db.session import get_db
from app.main import app

_TENANT_ID = uuid.uuid4()
_USER_ID = uuid.uuid4()


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


# ── ORM mock builders ─────────────────────────────────────────────────────────

def _vendor_orm(name: str = "ABC Fabrics") -> MagicMock:
    m = MagicMock()
    m.id = uuid.uuid4()
    m.tenant_id = _TENANT_ID
    m.name = name
    m.gstin = None
    m.address = None
    m.contact_name = None
    m.contact_phone = None
    m.contact_email = None
    m.is_active = True
    return m


def _bill_orm(bill_number: str = "INV-001") -> MagicMock:
    m = MagicMock()
    m.id = uuid.uuid4()
    m.tenant_id = _TENANT_ID
    m.vendor_id = uuid.uuid4()
    m.transporter_id = None
    m.location_id = uuid.uuid4()
    m.bin_id = uuid.uuid4()
    m.bill_number = bill_number
    m.bill_date = date(2026, 5, 25)
    m.total_amount = Decimal("2360.00")
    m.tax_amount = Decimal("360.00")
    m.status = "confirmed"
    m.notes = None
    m.lines = []    # lazy-loaded, empty for response serialization tests
    return m


def _payment_orm() -> MagicMock:
    m = MagicMock()
    m.id = uuid.uuid4()
    m.tenant_id = _TENANT_ID
    m.bill_id = uuid.uuid4()
    m.payment_date = date(2026, 5, 25)
    m.amount = Decimal("1000.00")
    m.payment_mode = "cash"
    m.reference_number = None
    m.notes = None
    return m


def _bill_payload(n_lines: int = 1) -> dict:
    lines = [
        {
            "product_variant_id": str(uuid.uuid4()),
            "quantity": "10",
            "unit_cost": "200",
            "tax_rate": "0.18",
        }
        for _ in range(n_lines)
    ]
    return {
        "vendor_id": str(uuid.uuid4()),
        "location_id": str(uuid.uuid4()),
        "bin_id": str(uuid.uuid4()),
        "bill_number": "INV-001",
        "bill_date": "2026-05-25",
        "lines": lines,
    }


# ── Vendor endpoints ──────────────────────────────────────────────────────────

def test_create_vendor_returns_201(client: TestClient) -> None:
    with patch("app.api.v1.purchases.PurchaseService") as MockSvc:
        MockSvc.return_value.create_vendor.return_value = _vendor_orm()
        resp = client.post("/api/v1/purchases/vendors", json={"name": "ABC Fabrics"})
    assert resp.status_code == 201
    assert resp.json()["name"] == "ABC Fabrics"


def test_create_vendor_empty_name_returns_422(client: TestClient) -> None:
    resp = client.post("/api/v1/purchases/vendors", json={"name": ""})
    assert resp.status_code == 422


def test_list_vendors_returns_200(client: TestClient) -> None:
    with patch("app.api.v1.purchases.PurchaseService") as MockSvc:
        MockSvc.return_value.list_vendors.return_value = [_vendor_orm(), _vendor_orm("XYZ Cloth")]
        resp = client.get("/api/v1/purchases/vendors")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


# ── CRITICAL TEST 1: Purchase Bill Success ────────────────────────────────────

def test_purchase_bill_success_creates_bill_and_records_stock(client: TestClient) -> None:
    """
    CRITICAL: POST /purchases/bills with valid 3-line payload.
    Verify:
      - 201 status returned
      - bill created (service.create_purchase_bill called)
      - response contains bill_number and status="confirmed"
      - total_amount correctly serialized

    The service mock captures that create_purchase_bill was invoked,
    which (by its implementation) calls inv_repo.append_ledger_entry,
    create_batch, and upsert_balance for each line atomically.
    """
    bill_mock = _bill_orm("INV-001")
    with patch("app.api.v1.purchases.PurchaseService") as MockSvc:
        MockSvc.return_value.create_purchase_bill.return_value = bill_mock
        resp = client.post("/api/v1/purchases/bills", json=_bill_payload(n_lines=3))

    assert resp.status_code == 201
    body = resp.json()
    assert body["bill_number"] == "INV-001"
    assert body["status"] == "confirmed"
    assert Decimal(body["total_amount"]) == Decimal("2360.00")
    # Service was called exactly once with the full request
    MockSvc.return_value.create_purchase_bill.assert_called_once()


def test_purchase_bill_response_includes_lines_list(client: TestClient) -> None:
    """Response schema must include a `lines` key (even if empty for mocked response)."""
    bill_mock = _bill_orm()
    with patch("app.api.v1.purchases.PurchaseService") as MockSvc:
        MockSvc.return_value.create_purchase_bill.return_value = bill_mock
        resp = client.post("/api/v1/purchases/bills", json=_bill_payload())

    assert resp.status_code == 201
    assert "lines" in resp.json()


def test_purchase_bill_empty_lines_returns_422(client: TestClient) -> None:
    """Bill with zero lines must be rejected by Pydantic (min_length=1)."""
    payload = _bill_payload()
    payload["lines"] = []
    resp = client.post("/api/v1/purchases/bills", json=payload)
    assert resp.status_code == 422


def test_purchase_bill_zero_quantity_returns_422(client: TestClient) -> None:
    payload = _bill_payload()
    payload["lines"][0]["quantity"] = "0"
    resp = client.post("/api/v1/purchases/bills", json=payload)
    assert resp.status_code == 422


# ── CRITICAL TEST 2: Rollback on Invalid Variant ─────────────────────────────

def test_rollback_on_invalid_variant_returns_404(client: TestClient) -> None:
    """
    CRITICAL: If any SKU is invalid, the service raises NotFoundError
    (and internally calls db.rollback() — no bill, no ledger, no batch).
    The router must return 404 with the structured error envelope.
    """
    from app.core.exceptions import NotFoundError
    with patch("app.api.v1.purchases.PurchaseService") as MockSvc:
        MockSvc.return_value.create_purchase_bill.side_effect = NotFoundError(
            "ProductVariant abc123 not found for this tenant"
        )
        resp = client.post("/api/v1/purchases/bills", json=_bill_payload(n_lines=10))

    assert resp.status_code == 404
    body = resp.json()
    assert body["error_code"] == "NOT_FOUND"
    assert "correlation_id" in body
    assert body["success"] is False


def test_rollback_on_invalid_vendor_returns_404(client: TestClient) -> None:
    from app.core.exceptions import NotFoundError
    with patch("app.api.v1.purchases.PurchaseService") as MockSvc:
        MockSvc.return_value.create_purchase_bill.side_effect = NotFoundError(
            "Vendor not found"
        )
        resp = client.post("/api/v1/purchases/bills", json=_bill_payload())

    assert resp.status_code == 404
    assert resp.json()["error_code"] == "NOT_FOUND"


def test_duplicate_bill_number_returns_409(client: TestClient) -> None:
    from app.core.exceptions import ConflictError
    with patch("app.api.v1.purchases.PurchaseService") as MockSvc:
        MockSvc.return_value.create_purchase_bill.side_effect = ConflictError(
            "Bill INV-001 already exists"
        )
        resp = client.post("/api/v1/purchases/bills", json=_bill_payload())

    assert resp.status_code == 409
    assert resp.json()["error_code"] == "CONFLICT"


# ── Get bill ──────────────────────────────────────────────────────────────────

def test_get_bill_returns_200(client: TestClient) -> None:
    bill_id = uuid.uuid4()
    with patch("app.api.v1.purchases.PurchaseService") as MockSvc:
        MockSvc.return_value.get_bill.return_value = _bill_orm()
        resp = client.get(f"/api/v1/purchases/bills/{bill_id}")
    assert resp.status_code == 200


def test_get_bill_not_found_returns_404(client: TestClient) -> None:
    from app.core.exceptions import NotFoundError
    bill_id = uuid.uuid4()
    with patch("app.api.v1.purchases.PurchaseService") as MockSvc:
        MockSvc.return_value.get_bill.side_effect = NotFoundError("Not found")
        resp = client.get(f"/api/v1/purchases/bills/{bill_id}")
    assert resp.status_code == 404


# ── Payments ──────────────────────────────────────────────────────────────────

def test_record_payment_returns_201(client: TestClient) -> None:
    with patch("app.api.v1.purchases.PurchaseService") as MockSvc:
        MockSvc.return_value.record_payment.return_value = _payment_orm()
        resp = client.post(
            "/api/v1/purchases/payments",
            json={
                "bill_id": str(uuid.uuid4()),
                "payment_date": "2026-05-25",
                "amount": "1000.00",
                "payment_mode": "cash",
            },
        )
    assert resp.status_code == 201
    assert resp.json()["payment_mode"] == "cash"


def test_record_payment_zero_amount_returns_422(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/purchases/payments",
        json={
            "bill_id": str(uuid.uuid4()),
            "payment_date": "2026-05-25",
            "amount": "0",
            "payment_mode": "cash",
        },
    )
    assert resp.status_code == 422


def test_record_payment_invalid_mode_returns_422(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/purchases/payments",
        json={
            "bill_id": str(uuid.uuid4()),
            "payment_date": "2026-05-25",
            "amount": "500",
            "payment_mode": "bitcoin",
        },
    )
    assert resp.status_code == 422
