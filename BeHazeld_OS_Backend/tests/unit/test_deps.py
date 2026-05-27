"""
API dependency tests — TenantContext, get_current_tenant, require_permission.
FastAPI's Depends wiring is not exercised here; each function is called directly.
"""
import uuid
from unittest.mock import MagicMock, patch

import pytest


def _make_ctx(is_superuser: bool = False, permissions: list[str] | None = None) -> "TenantContext":  # noqa: F821
    from app.api.deps import TenantContext
    return TenantContext(
        tenant_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        permissions=permissions or [],
        is_superuser=is_superuser,
    )


def _active_user(is_superuser: bool = False) -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.is_active = True
    u.is_superuser = is_superuser
    return u


# ── get_current_tenant ────────────────────────────────────────────────────────

def test_get_current_tenant_returns_context() -> None:
    from app.api.deps import get_current_tenant
    from app.core.exceptions import InvalidCredentialsError
    user = _active_user()
    payload = {
        "sub": str(user.id),
        "tenant_id": str(uuid.uuid4()),
        "type": "access",
        "permissions": ["catalog.view"],
    }
    credentials = MagicMock()
    credentials.credentials = "valid-token"
    with (
        patch("app.api.deps.security.decode_token", return_value=payload),
        patch("app.api.deps.UserRepository") as MockUR,
    ):
        MockUR.return_value.get_by_id.return_value = user
        ctx = get_current_tenant(credentials=credentials, db=MagicMock())
    assert ctx.user_id == user.id
    assert "catalog.view" in ctx.permissions


def test_get_current_tenant_rejects_refresh_token() -> None:
    from app.api.deps import get_current_tenant
    from app.core.exceptions import InvalidCredentialsError
    payload = {"sub": str(uuid.uuid4()), "tenant_id": str(uuid.uuid4()), "type": "refresh"}
    credentials = MagicMock()
    credentials.credentials = "refresh-token"
    with (
        patch("app.api.deps.security.decode_token", return_value=payload),
        patch("app.api.deps.UserRepository"),
    ):
        with pytest.raises(InvalidCredentialsError):
            get_current_tenant(credentials=credentials, db=MagicMock())


def test_get_current_tenant_rejects_inactive_user() -> None:
    from app.api.deps import get_current_tenant
    from app.core.exceptions import InvalidCredentialsError
    user = _active_user()
    user.is_active = False
    payload = {"sub": str(user.id), "tenant_id": str(uuid.uuid4()), "type": "access"}
    credentials = MagicMock()
    credentials.credentials = "token"
    with (
        patch("app.api.deps.security.decode_token", return_value=payload),
        patch("app.api.deps.UserRepository") as MockUR,
    ):
        MockUR.return_value.get_by_id.return_value = user
        with pytest.raises(InvalidCredentialsError):
            get_current_tenant(credentials=credentials, db=MagicMock())


# ── require_superuser ─────────────────────────────────────────────────────────

def test_require_superuser_passes_for_superuser() -> None:
    from app.api.deps import require_superuser
    ctx = _make_ctx(is_superuser=True)
    result = require_superuser(ctx=ctx)
    assert result is ctx


def test_require_superuser_raises_for_regular_user() -> None:
    from app.api.deps import require_superuser
    from app.core.exceptions import PermissionDeniedError
    ctx = _make_ctx(is_superuser=False)
    with pytest.raises(PermissionDeniedError):
        require_superuser(ctx=ctx)


# ── require_permission ────────────────────────────────────────────────────────

def test_require_permission_passes_when_code_present() -> None:
    from app.api.deps import require_permission
    dep = require_permission("catalog.view")
    ctx = _make_ctx(permissions=["catalog.view"])
    assert dep(ctx=ctx) is ctx


def test_require_permission_denied_when_code_absent() -> None:
    from app.api.deps import require_permission
    from app.core.exceptions import PermissionDeniedError
    dep = require_permission("catalog.delete")
    ctx = _make_ctx(permissions=["catalog.view"])
    with pytest.raises(PermissionDeniedError):
        dep(ctx=ctx)


def test_require_permission_superuser_bypasses_check() -> None:
    from app.api.deps import require_permission
    dep = require_permission("any.permission")
    ctx = _make_ctx(is_superuser=True, permissions=[])
    assert dep(ctx=ctx) is ctx


def test_require_permission_wildcard_bypasses_check() -> None:
    from app.api.deps import require_permission
    dep = require_permission("any.permission")
    ctx = _make_ctx(is_superuser=False, permissions=["*"])
    assert dep(ctx=ctx) is ctx


def test_require_permission_has_unique_name() -> None:
    from app.api.deps import require_permission
    dep1 = require_permission("orders.view")
    dep2 = require_permission("catalog.delete")
    assert dep1.__name__ != dep2.__name__
    assert "orders_view" in dep1.__name__
    assert "catalog_delete" in dep2.__name__
