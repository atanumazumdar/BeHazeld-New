"""Add image URL to catalog product variants.

Revision ID: 007
Revises: 006
Create Date: 2026-05-28
"""
from __future__ import annotations

from alembic import op


revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE IF EXISTS catalog.product_variants "
        "ADD COLUMN IF NOT EXISTS image_url VARCHAR(500)"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE IF EXISTS catalog.product_variants "
        "DROP COLUMN IF EXISTS image_url"
    )
