"""
Tenant repository — pure data access layer.
No business rules live here; all domain decisions belong in services.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.tenant import Location, Tenant


class TenantRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ── read ─────────────────────────────────────────────────────────────────

    def get_by_id(self, tenant_id: uuid.UUID) -> Tenant:
        tenant = self.db.scalar(select(Tenant).where(Tenant.id == tenant_id))
        if tenant is None:
            raise NotFoundError(f"Tenant {tenant_id} not found")
        return tenant

    def get_by_slug(self, slug: str) -> Tenant | None:
        return self.db.scalar(select(Tenant).where(Tenant.slug == slug))

    def list_all(self) -> list[Tenant]:
        return list(self.db.scalars(select(Tenant).order_by(Tenant.name)))

    # ── write ─────────────────────────────────────────────────────────────────

    def create(self, name: str, slug: str) -> Tenant:
        if self.get_by_slug(slug) is not None:
            raise ConflictError(f"Tenant with slug '{slug}' already exists")
        tenant = Tenant(name=name, slug=slug, is_active=True)
        self.db.add(tenant)
        self.db.flush()
        return tenant

    def list_locations_by_tenant(self, tenant_id: uuid.UUID) -> list[Location]:
        """Return all active locations for a tenant, ordered by name."""
        return list(
            self.db.scalars(
                select(Location)
                .where(Location.tenant_id == tenant_id, Location.is_active.is_(True))
                .order_by(Location.name)
            )
        )

    def set_active(self, tenant_id: uuid.UUID, is_active: bool) -> Tenant:
        tenant = self.get_by_id(tenant_id)
        tenant.is_active = is_active
        self.db.flush()
        return tenant
