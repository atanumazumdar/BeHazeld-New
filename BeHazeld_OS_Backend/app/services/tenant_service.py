"""
TenantService — tenant and user lifecycle management.

Last-admin guard
----------------
Deactivating a tenant's sole remaining active superuser would permanently
lock out that tenant.  The service checks before acting and raises
LastAdminError so the caller can surface a clear error.
"""
import uuid

from sqlalchemy.orm import Session

from app.core import security
from app.core.exceptions import LastAdminError, PermissionDeniedError
from app.repositories.identity_repository import UserRepository
from app.repositories.tenant_repository import TenantRepository
from app.schemas.admin import (
    CreateTenantRequest,
    CreateUserRequest,
    TenantResponse,
    UserListResponse,
)


class TenantService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.tenant_repo = TenantRepository(db)
        self.user_repo = UserRepository(db)

    # ── tenants ───────────────────────────────────────────────────────────────

    def create_tenant(self, request: CreateTenantRequest) -> TenantResponse:
        tenant = self.tenant_repo.create(name=request.name, slug=request.slug)
        self.db.commit()
        return TenantResponse.model_validate(tenant)

    def list_tenants(self) -> list[TenantResponse]:
        tenants = self.tenant_repo.list_all()
        return [TenantResponse.model_validate(t) for t in tenants]

    def deactivate_tenant(self, tenant_id: uuid.UUID) -> TenantResponse:
        tenant = self.tenant_repo.set_active(tenant_id, is_active=False)
        self.db.commit()
        return TenantResponse.model_validate(tenant)

    # ── users ─────────────────────────────────────────────────────────────────

    def create_admin_user(self, request: CreateUserRequest) -> UserListResponse:
        hashed_password = security.hash_password(request.password)
        user = self.user_repo.create(
            email=request.email,
            username=request.username,
            hashed_password=hashed_password,
            tenant_id=request.tenant_id,
            is_superuser=request.is_superuser,
        )
        self.db.commit()
        return UserListResponse.model_validate(user)

    def deactivate_user(self, tenant_id: uuid.UUID, user_id: uuid.UUID) -> UserListResponse:
        user = self.user_repo.get_by_id(user_id)

        if user.tenant_id != tenant_id:
            raise PermissionDeniedError("User does not belong to this tenant")

        if user.is_superuser:
            active_admin_count = self.user_repo.count_active_superusers_in_tenant(tenant_id)
            if active_admin_count <= 1:
                raise LastAdminError()

        updated_user = self.user_repo.set_active(user_id, is_active=False)
        self.db.commit()
        return UserListResponse.model_validate(updated_user)
