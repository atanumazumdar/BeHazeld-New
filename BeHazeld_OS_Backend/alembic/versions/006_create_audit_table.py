"""create audit schema and activity_log table

Revision ID: 006
Revises: 005
Create Date: 2026-05-26

Tables created (1 total):

  audit schema
  ─────────────────────────────────────────────────────
  1.  audit.activity_log  — one row per HTTP mutation (POST/PATCH/PUT/DELETE)
      tenant_id and user_id are nullable so public-API calls are also captured.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS audit")
    op.create_table(
        "activity_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("endpoint", sa.String(500), nullable=False),
        sa.Column("request_payload", sa.Text, nullable=True),
        sa.Column("response_status", sa.Integer, nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="audit",
    )
    op.create_index("ix_audit_log_tenant", "activity_log", ["tenant_id"], schema="audit")
    op.create_index("ix_audit_log_created", "activity_log", ["created_at"], schema="audit")


def downgrade() -> None:
    op.drop_table("activity_log", schema="audit")
    op.execute("DROP SCHEMA IF EXISTS audit")
