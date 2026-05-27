"""
FastAPI dependencies — tenant resolution and permission enforcement.

TenantContext is assembled from the JWT on every authenticated request.
No database lookup for tenant active-status here; that check happens at
login.  We only re-validate the user record to catch mid-session
deactivations.
"""
import uuid
from dataclasses import dataclass, field

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core import security
from app.core.exceptions import InvalidCredentialsError, PermissionDeniedError
from app.db.session import get_db
from app.repositories.identity_repository import UserRepository

_bearer = HTTPBearer()


@dataclass
class TenantContext:
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    permissions: list[str] = field(default_factory=list)
    is_superuser: bool = False


def get_current_tenant(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> TenantContext:
    token = credentials.credentials
    payload = security.decode_token(token)

    if payload.get("type") == "refresh":
        raise InvalidCredentialsError("Refresh tokens cannot authenticate requests")

    try:
        user_id = uuid.UUID(payload["sub"])
        tenant_id = uuid.UUID(payload["tenant_id"])
    except (KeyError, ValueError) as exc:
        raise InvalidCredentialsError("Malformed token claims") from exc

    user = UserRepository(db).get_by_id(user_id)
    if not user.is_active:
        raise InvalidCredentialsError("User account is inactive")

    permissions: list[str] = payload.get("permissions", [])
    return TenantContext(
        tenant_id=tenant_id,
        user_id=user_id,
        permissions=permissions,
        is_superuser=user.is_superuser,
    )


def require_superuser(
    ctx: TenantContext = Depends(get_current_tenant),
) -> TenantContext:
    if not ctx.is_superuser:
        raise PermissionDeniedError("Superuser access required")
    return ctx


def require_permission(permission_code: str):
    """
    Factory that returns a FastAPI dependency enforcing a specific permission.

    Superusers (is_superuser=True) and tokens carrying the wildcard "*"
    bypass the check.  Apply to any router endpoint:

        @router.get("/items", dependencies=[Depends(require_permission("catalog.items.view"))])
    """
    def _dependency(ctx: TenantContext = Depends(get_current_tenant)) -> TenantContext:
        if ctx.is_superuser or "*" in ctx.permissions or permission_code in ctx.permissions:
            return ctx
        raise PermissionDeniedError(f"Permission '{permission_code}' required")

    _dependency.__name__ = f"require_permission_{permission_code.replace('.', '_')}"
    return _dependency
