"""
TenantService tests.
Repositories are mocked; only service business logic is exercised.
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_db() -> MagicMock:
    return MagicMock()


def _tenant_orm(name: str = "Acme", slug: str = "acme") -> MagicMock:
    t = MagicMock()
    t.id = uuid.uuid4()
    t.name = name
    t.slug = slug
    t.is_active = True
    t.created_at = datetime.now(timezone.utc)
    return t


def _user_orm(is_superuser: bool = True, is_active: bool = True) -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.email = "admin@acme.com"
    u.username = "admin"
    u.is_active = is_active
    u.is_superuser = is_superuser
    u.tenant_id = uuid.uuid4()
    u.created_at = datetime.now(timezone.utc)
    return u


# ── create_tenant ─────────────────────────────────────────────────────────────

def test_create_tenant_returns_response_and_commits(mock_db: MagicMock) -> None:
    from app.services.tenant_service import TenantService
    from app.schemas.admin import CreateTenantRequest, TenantResponse
    tenant = _tenant_orm()
    with patch("app.services.tenant_service.TenantRepository") as MockTR:
        MockTR.return_value.create.return_value = tenant
        result = TenantService(mock_db).create_tenant(
            CreateTenantRequest(name="Acme", slug="acme")
        )
    assert isinstance(result, TenantResponse)
    mock_db.commit.assert_called_once()


def test_create_tenant_propagates_conflict_error(mock_db: MagicMock) -> None:
    from app.services.tenant_service import TenantService
    from app.schemas.admin import CreateTenantRequest
    from app.core.exceptions import ConflictError
    with patch("app.services.tenant_service.TenantRepository") as MockTR:
        MockTR.return_value.create.side_effect = ConflictError("Slug taken")
        with pytest.raises(ConflictError):
            TenantService(mock_db).create_tenant(
                CreateTenantRequest(name="Dup", slug="acme")
            )


# ── list_tenants ──────────────────────────────────────────────────────────────

def test_list_tenants_returns_all(mock_db: MagicMock) -> None:
    from app.services.tenant_service import TenantService
    from app.schemas.admin import TenantResponse
    tenants = [_tenant_orm(f"T{i}", f"t{i}") for i in range(4)]
    with patch("app.services.tenant_service.TenantRepository") as MockTR:
        MockTR.return_value.list_all.return_value = tenants
        result = TenantService(mock_db).list_tenants()
    assert len(result) == 4
    assert all(isinstance(r, TenantResponse) for r in result)


# ── deactivate_tenant ─────────────────────────────────────────────────────────

def test_deactivate_tenant_sets_inactive(mock_db: MagicMock) -> None:
    from app.services.tenant_service import TenantService
    tenant = _tenant_orm()
    tenant.is_active = False
    with patch("app.services.tenant_service.TenantRepository") as MockTR:
        MockTR.return_value.set_active.return_value = tenant
        result = TenantService(mock_db).deactivate_tenant(uuid.uuid4())
    assert result.is_active is False
    mock_db.commit.assert_called_once()


# ── create_admin_user ─────────────────────────────────────────────────────────

def test_create_admin_user_hashes_password_and_commits(mock_db: MagicMock) -> None:
    from app.services.tenant_service import TenantService
    from app.schemas.admin import CreateUserRequest, UserListResponse
    from app.core.security import verify_password
    user = _user_orm()
    tenant_id = uuid.uuid4()
    captured_hash: list[str] = []

    def capture_create(**kwargs):  # type: ignore[no-untyped-def]
        captured_hash.append(kwargs["hashed_password"])
        return user

    with patch("app.services.tenant_service.UserRepository") as MockUR:
        MockUR.return_value.create.side_effect = lambda **kw: (
            captured_hash.append(kw["hashed_password"]) or user
        )
        result = TenantService(mock_db).create_admin_user(
            CreateUserRequest(
                email="admin@acme.com",
                username="admin",
                password="Plaintext1!",
                tenant_id=tenant_id,
                is_superuser=True,
            )
        )
    assert isinstance(result, UserListResponse)
    # Password must have been hashed — bcrypt hashes are 60 chars starting with $2b$
    assert captured_hash[0].startswith("$2b$")
    assert verify_password("Plaintext1!", captured_hash[0])
    mock_db.commit.assert_called_once()


# ── deactivate_user — last-admin guard ───────────────────────────────────────

def test_deactivate_user_raises_last_admin_error(mock_db: MagicMock) -> None:
    """Cannot deactivate the sole remaining active admin of a tenant."""
    from app.services.tenant_service import TenantService
    from app.core.exceptions import LastAdminError
    user = _user_orm(is_superuser=True)
    with (
        patch("app.services.tenant_service.UserRepository") as MockUR,
        patch("app.services.tenant_service.TenantRepository"),
    ):
        MockUR.return_value.get_by_id.return_value = user
        MockUR.return_value.count_active_superusers_in_tenant.return_value = 1
        with pytest.raises(LastAdminError):
            TenantService(mock_db).deactivate_user(user.tenant_id, user.id)


def test_deactivate_user_succeeds_when_another_admin_exists(mock_db: MagicMock) -> None:
    """Deactivation is allowed when at least one other admin remains."""
    from app.services.tenant_service import TenantService
    from app.schemas.admin import UserListResponse
    user = _user_orm(is_superuser=True)
    user.is_active = False  # after set_active
    with (
        patch("app.services.tenant_service.UserRepository") as MockUR,
        patch("app.services.tenant_service.TenantRepository"),
    ):
        MockUR.return_value.get_by_id.return_value = user
        MockUR.return_value.count_active_superusers_in_tenant.return_value = 2
        MockUR.return_value.set_active.return_value = user
        result = TenantService(mock_db).deactivate_user(user.tenant_id, user.id)
    assert isinstance(result, UserListResponse)
    mock_db.commit.assert_called_once()


def test_deactivate_non_admin_user_skips_admin_count(mock_db: MagicMock) -> None:
    """The admin-count check is skipped for non-superuser accounts."""
    from app.services.tenant_service import TenantService
    from app.schemas.admin import UserListResponse
    user = _user_orm(is_superuser=False)
    user.is_active = False
    with (
        patch("app.services.tenant_service.UserRepository") as MockUR,
        patch("app.services.tenant_service.TenantRepository"),
    ):
        MockUR.return_value.get_by_id.return_value = user
        MockUR.return_value.set_active.return_value = user
        result = TenantService(mock_db).deactivate_user(user.tenant_id, user.id)
    # count_active_superusers_in_tenant must NOT have been called
    MockUR.return_value.count_active_superusers_in_tenant.assert_not_called()
    assert isinstance(result, UserListResponse)


def test_deactivate_user_rejects_cross_tenant(mock_db: MagicMock) -> None:
    """A user from a different tenant cannot be deactivated via this method."""
    from app.services.tenant_service import TenantService
    from app.core.exceptions import PermissionDeniedError
    user = _user_orm()
    user.tenant_id = uuid.uuid4()  # belongs to some other tenant
    different_tenant_id = uuid.uuid4()
    with (
        patch("app.services.tenant_service.UserRepository") as MockUR,
        patch("app.services.tenant_service.TenantRepository"),
    ):
        MockUR.return_value.get_by_id.return_value = user
        with pytest.raises(PermissionDeniedError):
            TenantService(mock_db).deactivate_user(different_tenant_id, user.id)
