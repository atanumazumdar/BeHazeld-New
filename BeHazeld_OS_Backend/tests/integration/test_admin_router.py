"""
Admin router integration tests.
Permission guards are exercised by injecting a TenantContext directly via
dependency_overrides; the service layer is mocked.
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.deps import TenantContext, get_current_tenant
from app.db.session import get_db
from app.main import app


@pytest.fixture
def mock_db() -> MagicMock:
    return MagicMock()


def _superuser_ctx() -> TenantContext:
    return TenantContext(
        tenant_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        permissions=["*"],
        is_superuser=True,
    )


def _regular_ctx(permissions: list[str] | None = None) -> TenantContext:
    return TenantContext(
        tenant_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        permissions=permissions or [],
        is_superuser=False,
    )


def _tenant_resp(name: str = "Acme", slug: str = "acme") -> dict:
    return {
        "id": str(uuid.uuid4()),
        "name": name,
        "slug": slug,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _user_resp(tenant_id: uuid.UUID | None = None) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "email": "admin@acme.com",
        "username": "admin",
        "is_active": True,
        "is_superuser": True,
        "tenant_id": str(tenant_id or uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def superuser_client(mock_db: MagicMock) -> TestClient:
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_tenant] = _superuser_ctx
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


@pytest.fixture
def regular_client(mock_db: MagicMock) -> TestClient:
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_tenant] = lambda: _regular_ctx()
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


# ── POST /admin/tenants ───────────────────────────────────────────────────────

def test_create_tenant_returns_201(superuser_client: TestClient) -> None:
    from app.schemas.admin import TenantResponse
    resp_data = _tenant_resp()
    with patch("app.api.v1.admin.TenantService") as MockSvc:
        MockSvc.return_value.create_tenant.return_value = TenantResponse(**resp_data)
        resp = superuser_client.post("/api/v1/admin/tenants", json={"name": "Acme", "slug": "acme"})
    assert resp.status_code == 201
    assert resp.json()["slug"] == "acme"


def test_create_tenant_forbidden_for_regular_user(regular_client: TestClient) -> None:
    resp = regular_client.post("/api/v1/admin/tenants", json={"name": "X", "slug": "x"})
    assert resp.status_code == 403


def test_create_tenant_conflict_returns_409(superuser_client: TestClient) -> None:
    from app.core.exceptions import ConflictError
    with patch("app.api.v1.admin.TenantService") as MockSvc:
        MockSvc.return_value.create_tenant.side_effect = ConflictError("Slug taken")
        resp = superuser_client.post("/api/v1/admin/tenants", json={"name": "Dup", "slug": "acme"})
    assert resp.status_code == 409
    assert resp.json()["error_code"] == "CONFLICT"


# ── GET /admin/tenants ────────────────────────────────────────────────────────

def test_list_tenants_returns_200(superuser_client: TestClient) -> None:
    from app.schemas.admin import TenantResponse
    tenants = [TenantResponse(**_tenant_resp(f"T{i}", f"t{i}")) for i in range(3)]
    with patch("app.api.v1.admin.TenantService") as MockSvc:
        MockSvc.return_value.list_tenants.return_value = tenants
        resp = superuser_client.get("/api/v1/admin/tenants")
    assert resp.status_code == 200
    assert len(resp.json()) == 3


# ── DELETE /admin/tenants/{tenant_id} ────────────────────────────────────────

def test_deactivate_tenant_returns_200(superuser_client: TestClient) -> None:
    from app.schemas.admin import TenantResponse
    resp_data = _tenant_resp()
    resp_data["is_active"] = False
    with patch("app.api.v1.admin.TenantService") as MockSvc:
        MockSvc.return_value.deactivate_tenant.return_value = TenantResponse(**resp_data)
        resp = superuser_client.delete(f"/api/v1/admin/tenants/{uuid.uuid4()}")
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


# ── POST /admin/tenants/{tenant_id}/users ─────────────────────────────────────

def test_create_user_returns_201(mock_db: MagicMock) -> None:
    from app.schemas.admin import UserListResponse
    tenant_id = uuid.uuid4()
    ctx = TenantContext(
        tenant_id=tenant_id, user_id=uuid.uuid4(),
        permissions=["admin.users.manage"], is_superuser=False,
    )
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_tenant] = lambda: ctx
    client = TestClient(app, raise_server_exceptions=False)

    user_data = _user_resp(tenant_id)
    with patch("app.api.v1.admin.TenantService") as MockSvc:
        MockSvc.return_value.create_admin_user.return_value = UserListResponse(**user_data)
        resp = client.post(
            f"/api/v1/admin/tenants/{tenant_id}/users",
            json={
                "email": "admin@acme.com",
                "username": "admin",
                "password": "Secret1!",
                "tenant_id": str(tenant_id),
                "is_superuser": True,
            },
        )
    app.dependency_overrides.clear()
    assert resp.status_code == 201


def test_create_user_forbidden_without_permission(regular_client: TestClient) -> None:
    resp = regular_client.post(
        f"/api/v1/admin/tenants/{uuid.uuid4()}/users",
        json={
            "email": "x@y.com", "username": "x",
            "password": "p", "tenant_id": str(uuid.uuid4()),
        },
    )
    assert resp.status_code == 403


# ── DELETE /admin/tenants/{tenant_id}/users/{user_id} ────────────────────────

def test_deactivate_user_last_admin_returns_409(mock_db: MagicMock) -> None:
    from app.core.exceptions import LastAdminError
    from app.schemas.admin import UserListResponse
    tenant_id = uuid.uuid4()
    ctx = TenantContext(
        tenant_id=tenant_id, user_id=uuid.uuid4(),
        permissions=["admin.users.manage"], is_superuser=True,
    )
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_tenant] = lambda: ctx
    client = TestClient(app, raise_server_exceptions=False)

    with patch("app.api.v1.admin.TenantService") as MockSvc:
        MockSvc.return_value.deactivate_user.side_effect = LastAdminError()
        resp = client.delete(f"/api/v1/admin/tenants/{tenant_id}/users/{uuid.uuid4()}")

    app.dependency_overrides.clear()
    assert resp.status_code == 409
    assert resp.json()["error_code"] == "LAST_ADMIN_ERROR"


# ── Health ────────────────────────────────────────────────────────────────────

def test_health_check_returns_ok() -> None:
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
