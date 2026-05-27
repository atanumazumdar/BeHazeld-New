"""
AuthService tests.
Repositories and security helpers are mocked; only service business logic is exercised.
"""
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_db() -> MagicMock:
    return MagicMock()


def _active_user(is_superuser: bool = False) -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.email = "user@test.com"
    u.hashed_password = "hashed"
    u.is_active = True
    u.is_superuser = is_superuser
    u.tenant_id = uuid.uuid4()
    u.roles = []
    return u


def _active_tenant() -> MagicMock:
    t = MagicMock()
    t.id = uuid.uuid4()
    t.is_active = True
    return t


def _valid_rt(user_id: uuid.UUID | None = None) -> MagicMock:
    rt = MagicMock()
    rt.user_id = user_id or uuid.uuid4()
    rt.revoked_at = None
    rt.expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    rt.is_valid = True
    return rt


# ── login ────────────────────────────────────────────────────────────────────

def test_login_returns_token_pair(mock_db: MagicMock) -> None:
    from app.services.auth_service import AuthService
    user, tenant = _active_user(), _active_tenant()
    with (
        patch("app.services.auth_service.UserRepository") as MockUR,
        patch("app.services.auth_service.TenantRepository") as MockTR,
        patch("app.services.auth_service.security.verify_password", return_value=True),
        patch("app.services.auth_service.security.create_access_token", return_value="acc"),
        patch("app.services.auth_service.security.create_refresh_token", return_value="ref"),
    ):
        MockUR.return_value.get_by_email.return_value = user
        MockTR.return_value.get_by_id.return_value = tenant
        result = AuthService(mock_db).login("user@test.com", "password")
    assert result.access_token == "acc"
    assert result.refresh_token == "ref"
    mock_db.commit.assert_called_once()


def test_login_raises_on_wrong_password(mock_db: MagicMock) -> None:
    from app.services.auth_service import AuthService
    from app.core.exceptions import InvalidCredentialsError
    user = _active_user()
    with (
        patch("app.services.auth_service.UserRepository") as MockUR,
        patch("app.services.auth_service.security.verify_password", return_value=False),
    ):
        MockUR.return_value.get_by_email.return_value = user
        with pytest.raises(InvalidCredentialsError):
            AuthService(mock_db).login("user@test.com", "wrong")


def test_login_raises_when_user_not_found(mock_db: MagicMock) -> None:
    from app.services.auth_service import AuthService
    from app.core.exceptions import InvalidCredentialsError
    with patch("app.services.auth_service.UserRepository") as MockUR:
        MockUR.return_value.get_by_email.return_value = None
        with pytest.raises(InvalidCredentialsError):
            AuthService(mock_db).login("ghost@b.com", "x")


def test_login_raises_when_user_inactive(mock_db: MagicMock) -> None:
    from app.services.auth_service import AuthService
    from app.core.exceptions import InvalidCredentialsError
    user = _active_user()
    user.is_active = False
    with (
        patch("app.services.auth_service.UserRepository") as MockUR,
        patch("app.services.auth_service.security.verify_password", return_value=True),
    ):
        MockUR.return_value.get_by_email.return_value = user
        with pytest.raises(InvalidCredentialsError):
            AuthService(mock_db).login("user@test.com", "pass")


def test_login_raises_when_tenant_inactive(mock_db: MagicMock) -> None:
    from app.services.auth_service import AuthService
    from app.core.exceptions import InvalidCredentialsError
    user, tenant = _active_user(), _active_tenant()
    tenant.is_active = False
    with (
        patch("app.services.auth_service.UserRepository") as MockUR,
        patch("app.services.auth_service.TenantRepository") as MockTR,
        patch("app.services.auth_service.security.verify_password", return_value=True),
    ):
        MockUR.return_value.get_by_email.return_value = user
        MockTR.return_value.get_by_id.return_value = tenant
        with pytest.raises(InvalidCredentialsError):
            AuthService(mock_db).login("user@test.com", "pass")


# ── refresh — happy path ──────────────────────────────────────────────────────

def test_refresh_rotates_tokens(mock_db: MagicMock) -> None:
    from app.services.auth_service import AuthService
    user = _active_user()
    rt = _valid_rt(user.id)
    payload = {"sub": str(user.id), "tenant_id": str(user.tenant_id), "type": "refresh"}
    with (
        patch("app.services.auth_service.UserRepository") as MockUR,
        patch("app.services.auth_service.security.decode_token", return_value=payload),
        patch("app.services.auth_service.security.create_access_token", return_value="new_acc"),
        patch("app.services.auth_service.security.create_refresh_token", return_value="new_ref"),
    ):
        MockUR.return_value.get_refresh_token.return_value = rt
        MockUR.return_value.get_by_id.return_value = user
        result = AuthService(mock_db).refresh("old-refresh-token")
    assert result.access_token == "new_acc"
    assert result.refresh_token == "new_ref"
    # Old token must be revoked, new token must be stored
    MockUR.return_value.revoke_refresh_token.assert_called_once_with("old-refresh-token")
    MockUR.return_value.store_refresh_token.assert_called_once()
    mock_db.commit.assert_called_once()


# ── refresh — token reuse detection ──────────────────────────────────────────

def test_refresh_detects_reuse_and_revokes_all_sessions(mock_db: MagicMock) -> None:
    """
    If the presented refresh token is already revoked, it signals possible theft.
    The service must revoke ALL tokens for that user and raise an error.
    """
    from app.services.auth_service import AuthService
    from app.core.exceptions import InvalidCredentialsError
    rt = _valid_rt()
    rt.revoked_at = datetime.now(timezone.utc)  # already revoked → reuse attempt
    with patch("app.services.auth_service.UserRepository") as MockUR:
        MockUR.return_value.get_refresh_token.return_value = rt
        with pytest.raises(InvalidCredentialsError) as exc_info:
            AuthService(mock_db).refresh("stolen-token")
    assert "reuse" in exc_info.value.message.lower()
    MockUR.return_value.revoke_all_refresh_tokens_for_user.assert_called_once_with(rt.user_id)
    mock_db.commit.assert_called_once()


def test_refresh_raises_when_token_not_found(mock_db: MagicMock) -> None:
    from app.services.auth_service import AuthService
    from app.core.exceptions import InvalidCredentialsError
    with patch("app.services.auth_service.UserRepository") as MockUR:
        MockUR.return_value.get_refresh_token.return_value = None
        with pytest.raises(InvalidCredentialsError):
            AuthService(mock_db).refresh("nonexistent-token")


def test_refresh_raises_on_wrong_token_type(mock_db: MagicMock) -> None:
    from app.services.auth_service import AuthService
    from app.core.exceptions import InvalidCredentialsError
    user = _active_user()
    rt = _valid_rt(user.id)
    payload = {"sub": str(user.id), "tenant_id": str(user.tenant_id), "type": "access"}
    with (
        patch("app.services.auth_service.UserRepository") as MockUR,
        patch("app.services.auth_service.security.decode_token", return_value=payload),
    ):
        MockUR.return_value.get_refresh_token.return_value = rt
        MockUR.return_value.get_by_id.return_value = user
        with pytest.raises(InvalidCredentialsError):
            AuthService(mock_db).refresh("access-token-used-as-refresh")


# ── logout ────────────────────────────────────────────────────────────────────

def test_logout_revokes_token_and_commits(mock_db: MagicMock) -> None:
    from app.services.auth_service import AuthService
    with patch("app.services.auth_service.UserRepository") as MockUR:
        AuthService(mock_db).logout("a-refresh-token")
    MockUR.return_value.revoke_refresh_token.assert_called_once_with("a-refresh-token")
    mock_db.commit.assert_called_once()


# ── get_current_user ──────────────────────────────────────────────────────────

def test_get_current_user_returns_user_response(mock_db: MagicMock) -> None:
    from app.services.auth_service import AuthService
    from app.schemas.auth import UserResponse
    user = _active_user()
    # Pydantic from_attributes needs real scalar values on these fields
    user.username = "testuser"
    user.email = "user@test.com"
    user.is_active = True
    user.is_superuser = False
    with patch("app.services.auth_service.UserRepository") as MockUR:
        MockUR.return_value.get_by_id.return_value = user
        result = AuthService(mock_db).get_current_user(user.id)
    assert isinstance(result, UserResponse)


# ── permission collection ─────────────────────────────────────────────────────

def test_superuser_gets_wildcard_permission(mock_db: MagicMock) -> None:
    from app.services.auth_service import AuthService
    user = _active_user(is_superuser=True)
    svc = AuthService(mock_db)
    perms = svc._collect_permissions(user)
    assert "*" in perms


def test_regular_user_gets_role_permissions(mock_db: MagicMock) -> None:
    from app.services.auth_service import AuthService
    user = _active_user()
    perm = MagicMock()
    perm.code = "catalog.products.view"
    role = MagicMock()
    role.permissions = [perm]
    user.roles = [role]
    svc = AuthService(mock_db)
    perms = svc._collect_permissions(user)
    assert "catalog.products.view" in perms
    assert "*" not in perms


def test_duplicate_permissions_are_deduplicated(mock_db: MagicMock) -> None:
    from app.services.auth_service import AuthService
    user = _active_user()
    perm = MagicMock()
    perm.code = "catalog.view"
    role1, role2 = MagicMock(), MagicMock()
    role1.permissions = [perm]
    role2.permissions = [perm]  # same code in two roles
    user.roles = [role1, role2]
    perms = AuthService(mock_db)._collect_permissions(user)
    assert perms.count("catalog.view") == 1
