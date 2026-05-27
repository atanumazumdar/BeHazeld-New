from __future__ import annotations

import os

from sqlalchemy import select, text

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.identity import (
    Permission,
    RefreshToken,
    Role,
    User,
    role_permissions_table,
    user_roles_table,
)
from app.models.tenant import Company, Location, Tenant


ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@behazeld.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin123!")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", ADMIN_EMAIL.split("@")[0])
TENANT_NAME = os.getenv("ADMIN_TENANT_NAME", "BeHazeld")
TENANT_SLUG = os.getenv("ADMIN_TENANT_SLUG", "behazeld")
SUPER_ADMIN_ROLE = "Super Admin"
WILDCARD_PERMISSION = "*"


def ensure_identity_tables() -> None:
    """Create the minimum schemas/tables required for the first login."""
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS tenant"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS identity"))

    Base.metadata.create_all(
        bind=engine,
        tables=[
            Tenant.__table__,
            Company.__table__,
            Location.__table__,
            User.__table__,
            Role.__table__,
            Permission.__table__,
            user_roles_table,
            role_permissions_table,
            RefreshToken.__table__,
        ],
    )


def get_or_create_tenant(db) -> Tenant:
    tenant = db.scalar(select(Tenant).where(Tenant.slug == TENANT_SLUG))
    if tenant is not None:
        tenant.name = TENANT_NAME
        tenant.is_active = True
        return tenant

    tenant = Tenant(name=TENANT_NAME, slug=TENANT_SLUG, is_active=True)
    db.add(tenant)
    db.flush()
    return tenant


def get_or_create_super_admin_role(db, tenant: Tenant) -> Role:
    role = db.scalar(
        select(Role).where(
            Role.tenant_id == tenant.id,
            Role.name == SUPER_ADMIN_ROLE,
        )
    )
    if role is None:
        role = Role(
            name=SUPER_ADMIN_ROLE,
            description="Bootstrap super administrator",
            tenant_id=tenant.id,
        )
        db.add(role)
        db.flush()

    permission = db.scalar(
        select(Permission).where(Permission.code == WILDCARD_PERMISSION)
    )
    if permission is None:
        permission = Permission(name="All permissions", code=WILDCARD_PERMISSION)
        db.add(permission)
        db.flush()

    if permission not in role.permissions:
        role.permissions.append(permission)
    return role


def create_or_update_admin_user(db, tenant: Tenant, role: Role) -> User:
    user = db.scalar(select(User).where(User.email == ADMIN_EMAIL))
    hashed_password = hash_password(ADMIN_PASSWORD)

    if user is None:
        user = User(
            email=ADMIN_EMAIL,
            username=ADMIN_USERNAME,
            hashed_password=hashed_password,
            tenant_id=tenant.id,
            is_active=True,
            is_superuser=True,
        )
        db.add(user)
        db.flush()
    else:
        user.username = ADMIN_USERNAME
        user.hashed_password = hashed_password
        user.tenant_id = tenant.id
        user.is_active = True
        user.is_superuser = True

    if role not in user.roles:
        user.roles.append(role)
    return user


def main() -> None:
    ensure_identity_tables()

    with SessionLocal() as db:
        tenant = get_or_create_tenant(db)
        role = get_or_create_super_admin_role(db, tenant)
        user = create_or_update_admin_user(db, tenant, role)
        db.commit()

        print("Super admin bootstrap complete.")
        print(f"Tenant: {tenant.name} ({tenant.slug})")
        print(f"Email: {user.email}")
        print("Password: set from ADMIN_PASSWORD env var or default Admin123!")


if __name__ == "__main__":
    main()
