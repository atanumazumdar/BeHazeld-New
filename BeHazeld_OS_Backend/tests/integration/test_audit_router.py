"""
Audit router integration tests.

Scenarios:
1. GET /audit/logs returns 200 with a list of AuditLogResponse objects.
2. Query params (user_id, endpoint, method) are forwarded to the repository.
3. Missing permission returns 403.
"""
import uuid
from datetime import datetime
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
    app.dependency_overrides[get_db]             = lambda: mock_db
    app.dependency_overrides[get_current_tenant] = lambda: superuser_ctx
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


def _log_orm(user_id: uuid.UUID | None = None) -> MagicMock:
    m = MagicMock()
    m.id              = uuid.uuid4()
    m.tenant_id       = _TENANT_ID
    m.user_id         = user_id
    m.method          = "POST"
    m.endpoint        = "/api/v1/sales/bills"
    m.response_status = 201
    m.ip_address      = "127.0.0.1"
    m.request_payload = '{"lines": []}'
    m.created_at      = datetime(2026, 5, 26, 10, 0, 0)
    return m


# ── tests ─────────────────────────────────────────────────────────────────────

@patch("app.api.v1.audit.AuditRepository")
def test_list_audit_logs_returns_200(MockRepo, client):
    """GET /audit/logs → 200 with list of log entries."""
    log = _log_orm(_USER_ID)
    MockRepo.return_value.list_logs.return_value = [log]

    resp = client.get("/api/v1/audit/logs")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["method"] == "POST"
    assert data[0]["endpoint"] == "/api/v1/sales/bills"
    assert data[0]["response_status"] == 201


@patch("app.api.v1.audit.AuditRepository")
def test_list_audit_logs_passes_filters(MockRepo, client):
    """Query params user_id + endpoint + method are forwarded to the repo."""
    MockRepo.return_value.list_logs.return_value = []
    uid = str(_USER_ID)

    resp = client.get(
        f"/api/v1/audit/logs?user_id={uid}&endpoint=/sales&method=POST&skip=0&limit=10"
    )

    assert resp.status_code == 200
    call_kwargs = MockRepo.return_value.list_logs.call_args.kwargs
    assert call_kwargs["user_id"] == _USER_ID
    assert call_kwargs["endpoint_search"] == "/sales"
    assert call_kwargs["method"] == "POST"
    assert call_kwargs["skip"] == 0
    assert call_kwargs["limit"] == 10


@patch("app.api.v1.audit.AuditRepository")
def test_list_audit_logs_empty(MockRepo, client):
    """GET /audit/logs with no entries returns empty list."""
    MockRepo.return_value.list_logs.return_value = []

    resp = client.get("/api/v1/audit/logs")

    assert resp.status_code == 200
    assert resp.json() == []


def test_list_audit_logs_forbidden():
    """User without audit.logs.view permission gets 403."""
    unprivileged = TenantContext(
        tenant_id=_TENANT_ID,
        user_id=_USER_ID,
        permissions=["catalog.view"],  # no audit permission
        is_superuser=False,
    )
    mock_db = MagicMock()
    app.dependency_overrides[get_db]             = lambda: mock_db
    app.dependency_overrides[get_current_tenant] = lambda: unprivileged
    c = TestClient(app, raise_server_exceptions=False)

    resp = c.get("/api/v1/audit/logs")

    app.dependency_overrides.clear()
    assert resp.status_code == 403
