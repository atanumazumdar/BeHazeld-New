"""create identity and tenant schemas and all Phase 1 tables

Revision ID: 001
Revises:
Create Date: 2026-05-25
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_schemas() -> None:
    """Create PostgreSQL schemas idempotently."""
    op.execute("CREATE SCHEMA IF NOT EXISTS identity")
    op.execute("CREATE SCHEMA IF NOT EXISTS tenant")


def upgrade() -> None:
    # ── Step 1: schemas must exist before any table is created ──────────────
    _create_schemas()

    # ── Step 2: tenant schema tables ────────────────────────────────────────
    # tenant.tenants — root table; identity.users has a FK into this
    op.create_table(
        "tenants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        schema="tenant",
    )
    op.create_index(
        "ix_tenant_tenants_slug", "tenants", ["slug"], unique=True, schema="tenant"
    )

    # tenant.companies
    op.create_table(
        "companies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenant.tenants.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("gstin", sa.String(20), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        schema="tenant",
    )
    op.create_index(
        "ix_tenant_companies_tenant_id", "companies", ["tenant_id"], schema="tenant"
    )

    # tenant.locations
    op.create_table(
        "locations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenant.tenants.id"),
            nullable=False,
        ),
        sa.Column(
            "company_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenant.companies.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        schema="tenant",
    )
    op.create_index(
        "ix_tenant_locations_tenant_id", "locations", ["tenant_id"], schema="tenant"
    )

    # ── Step 3: identity schema tables ──────────────────────────────────────
    # identity.users — depends on tenant.tenants FK
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("is_superuser", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenant.tenants.id"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        schema="identity",
    )
    op.create_index(
        "ix_identity_users_email", "users", ["email"], unique=True, schema="identity"
    )
    op.create_index(
        "ix_identity_users_username", "users", ["username"], unique=True, schema="identity"
    )
    op.create_index(
        "ix_identity_users_tenant_id", "users", ["tenant_id"], schema="identity"
    )

    # identity.roles
    op.create_table(
        "roles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenant.tenants.id"),
            nullable=False,
        ),
        schema="identity",
    )
    op.create_index(
        "ix_identity_roles_tenant_id", "roles", ["tenant_id"], schema="identity"
    )

    # identity.permissions
    op.create_table(
        "permissions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(255), nullable=False),
        schema="identity",
    )
    op.create_index(
        "ix_identity_permissions_code", "permissions", ["code"], unique=True, schema="identity"
    )

    # identity.user_roles — M2M join; depends on identity.users and identity.roles
    op.create_table(
        "user_roles",
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("identity.users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "role_id",
            UUID(as_uuid=True),
            sa.ForeignKey("identity.roles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        schema="identity",
    )

    # identity.role_permissions — M2M join; depends on identity.roles and identity.permissions
    op.create_table(
        "role_permissions",
        sa.Column(
            "role_id",
            UUID(as_uuid=True),
            sa.ForeignKey("identity.roles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "permission_id",
            UUID(as_uuid=True),
            sa.ForeignKey("identity.permissions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        schema="identity",
    )

    # identity.refresh_tokens — depends on identity.users
    op.create_table(
        "refresh_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("identity.users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        schema="identity",
    )
    op.create_index(
        "ix_identity_refresh_tokens_token_hash",
        "refresh_tokens",
        ["token_hash"],
        unique=True,
        schema="identity",
    )
    op.create_index(
        "ix_identity_refresh_tokens_user_id",
        "refresh_tokens",
        ["user_id"],
        schema="identity",
    )


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("refresh_tokens", schema="identity")
    op.drop_table("role_permissions", schema="identity")
    op.drop_table("user_roles", schema="identity")
    op.drop_table("permissions", schema="identity")
    op.drop_table("roles", schema="identity")
    op.drop_table("users", schema="identity")
    op.drop_table("locations", schema="tenant")
    op.drop_table("companies", schema="tenant")
    op.drop_table("tenants", schema="tenant")
    # Schemas are intentionally left; dropping a schema requires it to be empty
    # and is a destructive operation best done manually.
