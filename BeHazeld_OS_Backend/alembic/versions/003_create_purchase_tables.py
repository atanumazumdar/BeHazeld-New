"""create purchase schema and Phase 3 tables

Revision ID: 003
Revises: 002
Create Date: 2026-05-25

Tables created (5 total, in FK-dependency order):

  purchase schema
  ─────────────────────────────────────────────────────
  1.  purchase.vendors               ← FK → tenant.tenants
  2.  purchase.transporters          ← FK → tenant.tenants
  3.  purchase.purchase_bills        ← FKs → vendors, transporters, locations, bins
  4.  purchase.purchase_bill_lines   ← FKs → purchase_bills, product_variants
  5.  purchase.vendor_payments       ← FK  → purchase_bills

Notes
-----
- Schema creation uses the IF NOT EXISTS / EXEC pattern required by SQL Server.
- All PKs use PostgreSQL UUID defaults.
- downgrade() drops tables in reverse FK order, then drops the schema.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_schema() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS purchase")


def upgrade() -> None:
    _create_schema()

    # 1. purchase.vendors
    op.create_table(
        "vendors",
        sa.Column(
            "id", UUID(as_uuid=True),
            primary_key=True, server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id", UUID(as_uuid=True),
            sa.ForeignKey("tenant.tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(250), nullable=False),
        sa.Column("gstin", sa.String(20), nullable=True),
        sa.Column("address", sa.Text, nullable=True),
        sa.Column("contact_name", sa.String(150), nullable=True),
        sa.Column("contact_phone", sa.String(20), nullable=True),
        sa.Column("contact_email", sa.String(254), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "name", name="uq_purchase_vendors_tenant_name"),
        schema="purchase",
    )
    op.create_index("ix_purchase_vendors_tenant", "vendors", ["tenant_id"], schema="purchase")

    # 2. purchase.transporters
    op.create_table(
        "transporters",
        sa.Column(
            "id", UUID(as_uuid=True),
            primary_key=True, server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id", UUID(as_uuid=True),
            sa.ForeignKey("tenant.tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(250), nullable=False),
        sa.Column("vehicle_no", sa.String(50), nullable=True),
        sa.Column("contact_phone", sa.String(20), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        schema="purchase",
    )
    op.create_index("ix_purchase_transporters_tenant", "transporters", ["tenant_id"], schema="purchase")

    # 3. purchase.purchase_bills
    op.create_table(
        "purchase_bills",
        sa.Column(
            "id", UUID(as_uuid=True),
            primary_key=True, server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id", UUID(as_uuid=True),
            sa.ForeignKey("tenant.tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "vendor_id", UUID(as_uuid=True),
            sa.ForeignKey("purchase.vendors.id", ondelete="NO ACTION"),
            nullable=False,
        ),
        sa.Column(
            "transporter_id", UUID(as_uuid=True),
            sa.ForeignKey("purchase.transporters.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "location_id", UUID(as_uuid=True),
            sa.ForeignKey("tenant.locations.id", ondelete="NO ACTION"),
            nullable=False,
        ),
        sa.Column(
            "bin_id", UUID(as_uuid=True),
            sa.ForeignKey("inventory.bins.id", ondelete="NO ACTION"),
            nullable=False,
        ),
        sa.Column("bill_number", sa.String(100), nullable=False),
        sa.Column("bill_date", sa.Date, nullable=False),
        sa.Column("total_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("tax_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="'draft'"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "bill_number", name="uq_purchase_bills_tenant_number"),
        schema="purchase",
    )
    op.create_index("ix_purchase_bills_tenant", "purchase_bills", ["tenant_id"], schema="purchase")
    op.create_index("ix_purchase_bills_vendor", "purchase_bills", ["vendor_id"], schema="purchase")

    # 4. purchase.purchase_bill_lines
    op.create_table(
        "purchase_bill_lines",
        sa.Column(
            "id", UUID(as_uuid=True),
            primary_key=True, server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id", UUID(as_uuid=True),
            sa.ForeignKey("tenant.tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "bill_id", UUID(as_uuid=True),
            sa.ForeignKey("purchase.purchase_bills.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_variant_id", UUID(as_uuid=True),
            sa.ForeignKey("catalog.product_variants.id", ondelete="NO ACTION"),
            nullable=False,
        ),
        sa.Column("quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("unit_cost", sa.Numeric(14, 2), nullable=False),
        sa.Column("tax_rate", sa.Numeric(6, 4), nullable=False, server_default="0"),
        sa.Column("total_line_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("bill_id", "product_variant_id", name="uq_purchase_lines_bill_variant"),
        schema="purchase",
    )
    op.create_index("ix_purchase_lines_bill", "purchase_bill_lines", ["bill_id"], schema="purchase")
    op.create_index("ix_purchase_lines_variant", "purchase_bill_lines", ["product_variant_id"], schema="purchase")

    # 5. purchase.vendor_payments
    op.create_table(
        "vendor_payments",
        sa.Column(
            "id", UUID(as_uuid=True),
            primary_key=True, server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id", UUID(as_uuid=True),
            sa.ForeignKey("tenant.tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "bill_id", UUID(as_uuid=True),
            sa.ForeignKey("purchase.purchase_bills.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("payment_date", sa.Date, nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("payment_mode", sa.String(20), nullable=False),
        sa.Column("reference_number", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        schema="purchase",
    )
    op.create_index("ix_purchase_payments_bill", "vendor_payments", ["bill_id"], schema="purchase")
    op.create_index("ix_purchase_payments_tenant", "vendor_payments", ["tenant_id"], schema="purchase")


def downgrade() -> None:
    # Reverse FK order
    op.drop_table("vendor_payments", schema="purchase")
    op.drop_table("purchase_bill_lines", schema="purchase")
    op.drop_table("purchase_bills", schema="purchase")
    op.drop_table("transporters", schema="purchase")
    op.drop_table("vendors", schema="purchase")
    op.execute("DROP SCHEMA IF EXISTS purchase")
