"""
Auth router integration tests.
DB dependency is overridden with a MagicMock; service layer is mocked so
these tests exercise the HTTP contract (status codes, response shapes,
header handling) without requiring a live database.
"""
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_db


@pytest.fixture
def mock_db() -> MagicMock:
    return MagicMock()


@pytest.fixture
def client(mock_db: MagicMock) -> TestClient:
    app.dependency_overrides[get_db] = lambda: mock_db
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


def _token_response() -> dict:
    return {"access_token": "acc", "refresh_token": "ref", "token_type": "bearer"}


# ── POST /auth/login ──────────────────────────────────────────────────────────

def test_login_returns_200_with_tokens(client: TestClient) -> None:
    from app.schemas.auth import TokenResponse
    with patch("app.api.v1.auth.AuthService") as MockSvc:
        MockSvc.return_value.login.return_value = TokenResponse(**_token_response())
        resp = client.post("/api/v1/auth/login", json={"email": "a@b.com", "password": "pass"})
    assert resp.status_code == 200
    assert resp.json()["access_token"] == "acc"
    assert resp.json()["token_type"] == "bearer"


def test_login_invalid_credentials_returns_401(client: TestClient) -> None:
    from app.core.exceptions import InvalidCredentialsError
    with patch("app.api.v1.auth.AuthService") as MockSvc:
        MockSvc.return_value.login.side_effect = InvalidCredentialsError("Bad creds")
        resp = client.post("/api/v1/auth/login", json={"email": "a@b.com", "password": "x"})
    assert resp.status_code == 401
    body = resp.json()
    assert body["error_code"] == "INVALID_CREDENTIALS"
    assert "correlation_id" in body


def test_login_missing_field_returns_422(client: TestClient) -> None:
    resp = client.post("/api/v1/auth/login", json={"email": "a@b.com"})
    assert resp.status_code == 422


# ── POST /auth/refresh ────────────────────────────────────────────────────────

def test_refresh_returns_new_tokens(client: TestClient) -> None:
    from app.schemas.auth import TokenResponse
    with patch("app.api.v1.auth.AuthService") as MockSvc:
        MockSvc.return_value.refresh.return_value = TokenResponse(
            access_token="new_acc", refresh_token="new_ref"
        )
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "old-ref"})
    assert resp.status_code == 200
    assert resp.json()["access_token"] == "new_acc"


def test_refresh_reuse_returns_401(client: TestClient) -> None:
    from app.core.exceptions import InvalidCredentialsError
    with patch("app.api.v1.auth.AuthService") as MockSvc:
        MockSvc.return_value.refresh.side_effect = InvalidCredentialsError(
            "Refresh token reuse detected"
        )
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "stolen"})
    assert resp.status_code == 401


# ── POST /auth/logout ─────────────────────────────────────────────────────────

def test_logout_returns_204(client: TestClient) -> None:
    with patch("app.api.v1.auth.AuthService") as MockSvc:
        MockSvc.return_value.logout.return_value = None
        resp = client.post("/api/v1/auth/logout", json={"refresh_token": "ref"})
    assert resp.status_code == 204
    assert resp.content == b""


# ── GET /auth/me ──────────────────────────────────────────────────────────────

def test_me_returns_user(client: TestClient) -> None:
    from app.api.deps import get_current_tenant, TenantContext
    from app.schemas.auth import UserResponse

    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    ctx = TenantContext(tenant_id=tenant_id, user_id=user_id, permissions=[], is_superuser=False)
    user = UserResponse(
        id=user_id, email="a@b.com", username="alice",
        is_active=True, is_superuser=False, tenant_id=tenant_id,
    )

    app.dependency_overrides[get_current_tenant] = lambda: ctx
    with patch("app.api.v1.auth.AuthService") as MockSvc:
        MockSvc.return_value.get_current_user.return_value = user
        resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer tok"})
    app.dependency_overrides.pop(get_current_tenant, None)

    assert resp.status_code == 200
    assert resp.json()["email"] == "a@b.com"


def test_me_without_token_returns_401_or_403(client: TestClient) -> None:
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code in (401, 403)
