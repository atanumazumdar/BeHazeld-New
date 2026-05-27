import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest


# ── auth schemas ─────────────────────────────────────────────────────────────

def test_login_request_rejects_invalid_email() -> None:
    from pydantic import ValidationError
    from app.schemas.auth import LoginRequest
    with pytest.raises(ValidationError):
        LoginRequest(email="not-an-email", password="secret")


def test_login_request_accepts_valid_email() -> None:
    from app.schemas.auth import LoginRequest
    req = LoginRequest(email="user@example.com", password="secret")
    assert req.email == "user@example.com"


def test_token_response_defaults_to_bearer() -> None:
    from app.schemas.auth import TokenResponse
    t = TokenResponse(access_token="acc", refresh_token="ref")
    assert t.token_type == "bearer"


def test_user_response_builds_from_orm_object() -> None:
    from app.schemas.auth import UserResponse
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "a@b.com"
    user.username = "ab"
    user.is_active = True
    user.is_superuser = False
    user.tenant_id = uuid.uuid4()
    resp = UserResponse.model_validate(user)
    assert resp.email == "a@b.com"
    assert isinstance(resp.id, uuid.UUID)


def test_token_data_permissions_default_empty() -> None:
    from app.schemas.auth import TokenData
    td = TokenData(sub="user-id", tenant_id="tenant-id")
    assert td.permissions == []
    assert td.type == "access"


def test_refresh_request_holds_token() -> None:
    from app.schemas.auth import RefreshRequest
    r = RefreshRequest(refresh_token="tok")
    assert r.refresh_token == "tok"


# ── admin schemas ─────────────────────────────────────────────────────────────

def test_create_tenant_request() -> None:
    from app.schemas.admin import CreateTenantRequest
    req = CreateTenantRequest(name="Acme Corp", slug="acme-corp")
    assert req.slug == "acme-corp"


def test_tenant_response_builds_from_orm() -> None:
    from app.schemas.admin import TenantResponse
    tenant = MagicMock()
    tenant.id = uuid.uuid4()
    tenant.name = "Acme"
    tenant.slug = "acme"
    tenant.is_active = True
    tenant.created_at = datetime.now(timezone.utc)
    resp = TenantResponse.model_validate(tenant)
    assert resp.slug == "acme"
    assert isinstance(resp.id, uuid.UUID)


def test_create_user_request_defaults_is_superuser_false() -> None:
    from app.schemas.admin import CreateUserRequest
    req = CreateUserRequest(
        email="u@a.com", username="u", password="p", tenant_id=uuid.uuid4()
    )
    assert req.is_superuser is False


def test_user_list_response_builds_from_orm() -> None:
    from app.schemas.admin import UserListResponse
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "u@a.com"
    user.username = "u"
    user.is_active = True
    user.is_superuser = False
    user.tenant_id = uuid.uuid4()
    user.created_at = datetime.now(timezone.utc)
    resp = UserListResponse.model_validate(user)
    assert resp.email == "u@a.com"


def test_update_user_request_all_fields_optional() -> None:
    from app.schemas.admin import UpdateUserRequest
    req = UpdateUserRequest()
    assert req.is_active is None
    assert req.is_superuser is None


# ── common schemas ────────────────────────────────────────────────────────────

def test_error_response_success_is_false() -> None:
    from app.schemas.common import ErrorResponse
    err = ErrorResponse(error_code="NOT_FOUND", message="Gone")
    assert err.success is False
    assert err.correlation_id is None


def test_success_response_defaults() -> None:
    from app.schemas.common import SuccessResponse
    ok = SuccessResponse()
    assert ok.success is True
    assert ok.message == "OK"


def test_paginated_response_holds_items() -> None:
    from app.schemas.common import PaginatedResponse
    p = PaginatedResponse(items=[1, 2, 3], total=3, page=1, size=10, pages=1)
    assert len(p.items) == 3
