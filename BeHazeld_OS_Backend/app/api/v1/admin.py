"""
Admin router — tenant and user lifecycle management.

Permission model
----------------
Every endpoint requires either require_superuser (platform-wide ops like
creating tenants) or a specific named permission so the permission model
can be extended to non-superuser admin roles later without router changes.

    admin.tenants.manage  — create / deactivate tenants
    admin.users.manage    — create / deactivate users within a tenant
    admin.users.list      — read-only listing of users
"""
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import TenantContext, require_permission, require_superuser
from app.db.session import get_db
from app.schemas.admin import (
    CreateTenantRequest,
    CreateUserRequest,
    TenantResponse,
    UserListResponse,
)
from app.services.tenant_service import TenantService

router = APIRouter(prefix="/admin", tags=["admin"])

# ── tenant management (platform-wide — superuser only) ────────────────────────

@router.post(
    "/tenants",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_superuser)],
)
def create_tenant(
    body: CreateTenantRequest,
    db: Session = Depends(get_db),
) -> TenantResponse:
    return TenantService(db).create_tenant(body)


@router.get(
    "/tenants",
    response_model=list[TenantResponse],
    dependencies=[Depends(require_superuser)],
)
def list_tenants(db: Session = Depends(get_db)) -> list[TenantResponse]:
    return TenantService(db).list_tenants()


@router.delete(
    "/tenants/{tenant_id}",
    response_model=TenantResponse,
    dependencies=[Depends(require_superuser)],
)
def deactivate_tenant(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> TenantResponse:
    return TenantService(db).deactivate_tenant(tenant_id)


# ── user management (tenant-scoped) ──────────────────────────────────────────

@router.post(
    "/tenants/{tenant_id}/users",
    response_model=UserListResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("admin.users.manage"))],
)
def create_user(
    tenant_id: uuid.UUID,
    body: CreateUserRequest,
    db: Session = Depends(get_db),
) -> UserListResponse:
    # Bind tenant_id from the path — ignores any tenant_id in body
    body = body.model_copy(update={"tenant_id": tenant_id})
    return TenantService(db).create_admin_user(body)


@router.get(
    "/tenants/{tenant_id}/users",
    response_model=list[UserListResponse],
    dependencies=[Depends(require_permission("admin.users.list"))],
)
def list_users(
    tenant_id: uuid.UUID,
    ctx: TenantContext = Depends(require_permission("admin.users.list")),
    db: Session = Depends(get_db),
) -> list[UserListResponse]:
    from app.repositories.identity_repository import UserRepository
    users = UserRepository(db).get_by_tenant(tenant_id)
    return [UserListResponse.model_validate(u) for u in users]


@router.delete(
    "/tenants/{tenant_id}/users/{user_id}",
    response_model=UserListResponse,
    dependencies=[Depends(require_permission("admin.users.manage"))],
)
def deactivate_user(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> UserListResponse:
    return TenantService(db).deactivate_user(tenant_id, user_id)
