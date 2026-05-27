"""
Sales router integration tests.

CRITICAL scenarios:
1. "The Golden Sale" — POST /sales/bills returns 201, bill created,
   service.create_sale called once with all data, PDF metadata implied.
2. "Partial Stock Failure" — StockNotAvailableError → 409 with structured
   error envelope; no commit.

Additional: PDF endpoint returns application/pdf content-type.
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
_USER_ID   = uuid.uuid4()


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
    app.dependency_overrides[get_db]              = lambda: mock_db
    app.dependency_overrides[get_current_tenant]  = lambda: superuser_ctx
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


# ── ORM mock builders ─────────────────────────────────────────────────────────

def _bill_orm(invoice_number: str = "INV-000001") -> MagicMock:
    m = MagicMock()
    m.id              = uuid.uuid4()
    m.tenant_id       = _TENANT_ID
    m.customer_id     = None
    m.location_id     = uuid.uuid4()
    m.bin_id          = uuid.uuid4()
    m.invoice_number  = invoice_number
    m.bill_date       = date(2026, 5, 25)
    m.total_amount    = Decimal("2360.00")
    m.tax_amount      = Decimal("360.00")
    m.total_discount  = Decimal("0.00")
    m.status          = "confirmed"
    m.notes           = None
    m.lines           = []
    m.payments        = []
    return m


def _customer_orm() -> MagicMock:
    m = MagicMock()
    m.id             = uuid.uuid4()
    m.tenant_id      = _TENANT_ID
    m.name           = "Priya Sharma"
    m.email          = "priya@example.com"
    m.phone          = "9876543210"
    m.address        = None
    m.loyalty_points = 0
    m.is_active      = True
    return m


def _sale_payload(n_lines: int = 2) -> dict:
    return {
        "location_id": str(uuid.uuid4()),
        "bin_id":      str(uuid.uuid4()),
        "bill_date":   "2026-05-25",
        "lines": [
            {
                "product_variant_id": str(uuid.uuid4()),
                "quantity":        "3",
                "selling_price":   "500",
                "tax_rate":        "0.18",
                "discount_amount": "0",
            }
            for _ in range(n_lines)
        ],
        "payment": {
            "amount":       "3540.00",
            "payment_mode": "cash",
        },
    }


# ── Customer endpoints ────────────────────────────────────────────────────────

def test_create_customer_returns_201(client: TestClient) -> None:
    with patch("app.api.v1.sales.SalesService") as MockSvc:
        MockSvc.return_value.create_customer.return_value = _customer_orm()
        resp = client.post("/api/v1/sales/customers", json={"name": "Priya Sharma"})
    assert resp.status_code == 201
    assert resp.json()["name"] == "Priya Sharma"


def test_create_customer_empty_name_returns_422(client: TestClient) -> None:
    resp = client.post("/api/v1/sales/customers", json={"name": ""})
    assert resp.status_code == 422


def test_list_customers_returns_200(client: TestClient) -> None:
    with patch("app.api.v1.sales.SalesService") as MockSvc:
        MockSvc.return_value.list_customers.return_value = [_customer_orm()]
        resp = client.get("/api/v1/sales/customers")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


# ── CRITICAL TEST 1: The Golden Sale ─────────────────────────────────────────

def test_golden_sale_returns_201_with_confirmed_bill(client: TestClient) -> None:
    """
    THE GOLDEN SALE: valid 2-item sale.
    Verify:
      - 201 status
      - bill has invoice_number, status=confirmed
      - service.create_sale called exactly once
    The service mock implies stock deducted → bill → payment → PDF.
    """
    bill_mock = _bill_orm("INV-000001")
    metadata_mock = MagicMock()
    metadata_mock.invoice_number  = "INV-000001"
    metadata_mock.file_path       = "/var/invoices/INV-000001.pdf"
    metadata_mock.file_size_bytes = 3000

    with patch("app.api.v1.sales.SalesService") as MockSvc:
        MockSvc.return_value.create_sale.return_value = (bill_mock, metadata_mock)
        resp = client.post("/api/v1/sales/bills", json=_sale_payload(n_lines=2))

    assert resp.status_code == 201
    body = resp.json()
    assert body["invoice_number"] == "INV-000001"
    assert body["status"] == "confirmed"
    assert Decimal(body["total_amount"]) == Decimal("2360.00")
    MockSvc.return_value.create_sale.assert_called_once()


def test_golden_sale_response_contains_lines_and_payments(client: TestClient) -> None:
    """Response schema must include `lines` and `payments` keys."""
    bill_mock = _bill_orm()
    with patch("app.api.v1.sales.SalesService") as MockSvc:
        MockSvc.return_value.create_sale.return_value = (bill_mock, MagicMock())
        resp = client.post("/api/v1/sales/bills", json=_sale_payload())
    assert resp.status_code == 201
    body = resp.json()
    assert "lines" in body
    assert "payments" in body


def test_golden_sale_empty_lines_returns_422(client: TestClient) -> None:
    payload = _sale_payload()
    payload["lines"] = []
    resp = client.post("/api/v1/sales/bills", json=payload)
    assert resp.status_code == 422


def test_golden_sale_zero_quantity_returns_422(client: TestClient) -> None:
    payload = _sale_payload(n_lines=1)
    payload["lines"][0]["quantity"] = "0"
    resp = client.post("/api/v1/sales/bills", json=payload)
    assert resp.status_code == 422


def test_golden_sale_zero_selling_price_returns_422(client: TestClient) -> None:
    payload = _sale_payload(n_lines=1)
    payload["lines"][0]["selling_price"] = "0"
    resp = client.post("/api/v1/sales/bills", json=payload)
    assert resp.status_code == 422


# ── CRITICAL TEST 2: Partial Stock Failure ────────────────────────────────────

def test_partial_stock_failure_returns_409(client: TestClient) -> None:
    """
    PARTIAL STOCK FAILURE: 3-item sale where stock is short.
    Service raises StockNotAvailableError → router returns 409 with
    error_code=SALE_STOCK_NOT_AVAILABLE and correlation_id.
    """
    from app.core.exceptions import StockNotAvailableError
    with patch("app.api.v1.sales.SalesService") as MockSvc:
        MockSvc.return_value.create_sale.side_effect = StockNotAvailableError(
            "Only 2 units available for variant abc123; requested 5"
        )
        resp = client.post("/api/v1/sales/bills", json=_sale_payload(n_lines=3))

    assert resp.status_code == 409
    body = resp.json()
    assert body["error_code"] == "SALE_STOCK_NOT_AVAILABLE"
    assert body["success"] is False
    assert "correlation_id" in body
    assert "2 units" in body["message"]


def test_partial_stock_failure_error_envelope_is_complete(client: TestClient) -> None:
    """The 409 body must have success=False, error_code, message, correlation_id."""
    from app.core.exceptions import StockNotAvailableError
    with patch("app.api.v1.sales.SalesService") as MockSvc:
        MockSvc.return_value.create_sale.side_effect = StockNotAvailableError()
        resp = client.post("/api/v1/sales/bills", json=_sale_payload())
    body = resp.json()
    for field in ("success", "error_code", "message", "correlation_id"):
        assert field in body, f"Missing field: {field}"
    assert body["success"] is False


# ── Additional failure paths ──────────────────────────────────────────────────

def test_invalid_variant_returns_404(client: TestClient) -> None:
    from app.core.exceptions import NotFoundError
    with patch("app.api.v1.sales.SalesService") as MockSvc:
        MockSvc.return_value.create_sale.side_effect = NotFoundError("Variant missing")
        resp = client.post("/api/v1/sales/bills", json=_sale_payload())
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "NOT_FOUND"


def test_invalid_payment_mode_returns_422(client: TestClient) -> None:
    payload = _sale_payload()
    payload["payment"]["payment_mode"] = "crypto"
    resp = client.post("/api/v1/sales/bills", json=payload)
    assert resp.status_code == 422


def test_zero_payment_amount_returns_422(client: TestClient) -> None:
    payload = _sale_payload()
    payload["payment"]["amount"] = "0"
    resp = client.post("/api/v1/sales/bills", json=payload)
    assert resp.status_code == 422


# ── PDF endpoint ──────────────────────────────────────────────────────────────

def test_get_invoice_pdf_returns_pdf_bytes(client: TestClient) -> None:
    bill_id = uuid.uuid4()
    with patch("app.api.v1.sales.SalesService") as MockSvc:
        MockSvc.return_value.get_invoice_pdf.return_value = b"%PDF-1.4 test"
        resp = client.get(f"/api/v1/sales/bills/{bill_id}/pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content == b"%PDF-1.4 test"


def test_get_invoice_pdf_not_found_returns_404(client: TestClient) -> None:
    from app.core.exceptions import NotFoundError
    bill_id = uuid.uuid4()
    with patch("app.api.v1.sales.SalesService") as MockSvc:
        MockSvc.return_value.get_invoice_pdf.side_effect = NotFoundError("Bill not found")
        resp = client.get(f"/api/v1/sales/bills/{bill_id}/pdf")
    assert resp.status_code == 404


# ── List and get bills ────────────────────────────────────────────────────────

def test_list_bills_returns_200(client: TestClient) -> None:
    with patch("app.api.v1.sales.SalesService") as MockSvc:
        MockSvc.return_value.list_bills.return_value = [_bill_orm(), _bill_orm("INV-000002")]
        resp = client.get("/api/v1/sales/bills")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_get_bill_not_found_returns_404(client: TestClient) -> None:
    from app.core.exceptions import NotFoundError
    bill_id = uuid.uuid4()
    with patch("app.api.v1.sales.SalesService") as MockSvc:
        MockSvc.return_value.get_bill.side_effect = NotFoundError("Not found")
        resp = client.get(f"/api/v1/sales/bills/{bill_id}")
    assert resp.status_code == 404
