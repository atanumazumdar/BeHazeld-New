"""create finance schema and Phase 4b tables

Revision ID: 005
Revises: 004
Create Date: 2026-05-25

Tables created (3 total, in FK-dependency order):

  finance schema
  ─────────────────────────────────────────────────────
  1.  finance.chart_of_accounts  ← FK → tenant.tenants, self-referential parent_id
  2.  finance.journal_entries    ← FK → tenant.tenants
  3.  finance.journal_lines      ← FKs → journal_entries, chart_of_accounts
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS finance")

    op.create_table(
        "chart_of_accounts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenant.tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_id", UUID(as_uuid=True), sa.ForeignKey("finance.chart_of_accounts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("account_code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(250), nullable=False),
        sa.Column("account_type", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("tenant_id", "account_code", name="uq_finance_coa_tenant_code"),
        schema="finance",
    )
    op.create_index("ix_finance_coa_tenant", "chart_of_accounts", ["tenant_id"], schema="finance")

    op.create_table(
        "journal_entries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenant.tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entry_number", sa.String(30), nullable=False),
        sa.Column("entry_date", sa.Date, nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("ref_type", sa.String(20), nullable=False),
        sa.Column("ref_id", UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="posted"),
        sa.UniqueConstraint("tenant_id", "entry_number", name="uq_finance_journal_tenant_number"),
        schema="finance",
    )
    op.create_index("ix_finance_journal_tenant", "journal_entries", ["tenant_id"], schema="finance")
    op.create_index("ix_finance_journal_ref", "journal_entries", ["ref_type", "ref_id"], schema="finance")

    op.create_table(
        "journal_lines",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenant.tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("journal_id", UUID(as_uuid=True), sa.ForeignKey("finance.journal_entries.id", ondelete="NO ACTION"), nullable=False),
        sa.Column("account_id", UUID(as_uuid=True), sa.ForeignKey("finance.chart_of_accounts.id", ondelete="NO ACTION"), nullable=False),
        sa.Column("debit_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("credit_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("memo", sa.Text, nullable=True),
        schema="finance",
    )
    op.create_index("ix_finance_jline_journal", "journal_lines", ["journal_id"], schema="finance")
    op.create_index("ix_finance_jline_account", "journal_lines", ["account_id"], schema="finance")


def downgrade() -> None:
    op.drop_table("journal_lines", schema="finance")
    op.drop_table("journal_entries", schema="finance")
    op.drop_table("chart_of_accounts", schema="finance")
    op.execute("DROP SCHEMA IF EXISTS finance")
