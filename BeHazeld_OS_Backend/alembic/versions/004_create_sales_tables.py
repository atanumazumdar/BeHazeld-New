"""create sales schema and Phase 4 tables

Revision ID: 004
Revises: 003
Create Date: 2026-05-25

Tables created (4 total, in FK-dependency order):

  sales schema
  ─────────────────────────────────────────────────────
  1.  sales.customers       ← FK → tenant.tenants
  2.  sales.sale_bills      ← FKs → customers, locations, bins
  3.  sales.sale_bill_lines ← FKs → sale_bills, product_variants
  4.  sales.sale_payments   ← FK  → sale_bills
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_schema() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS sales")


def upgrade() -> None:
    _create_schema()

    # 1. sales.customers
    op.create_table(
        "customers",
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
        sa.Column("email", sa.String(254), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("address", sa.Text, nullable=True),
        sa.Column("loyalty_points", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "email", name="uq_sales_customers_tenant_email"),
        schema="sales",
    )
    op.create_index("ix_sales_customers_tenant", "customers", ["tenant_id"], schema="sales")
    op.create_index("ix_sales_customers_phone", "customers", ["phone"], schema="sales")

    # 2. sales.sale_bills
    op.create_table(
        "sale_bills",
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
            "customer_id", UUID(as_uuid=True),
            sa.ForeignKey("sales.customers.id", ondelete="SET NULL"),
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
        sa.Column("invoice_number", sa.String(50), nullable=False),
        sa.Column("bill_date", sa.Date, nullable=False),
        sa.Column("total_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("tax_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("total_discount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="'confirmed'"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "invoice_number", name="uq_sales_bills_tenant_invoice"),
        schema="sales",
    )
    op.create_index("ix_sales_bills_tenant", "sale_bills", ["tenant_id"], schema="sales")
    op.create_index("ix_sales_bills_customer", "sale_bills", ["customer_id"], schema="sales")

    # 3. sales.sale_bill_lines
    op.create_table(
        "sale_bill_lines",
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
            sa.ForeignKey("sales.sale_bills.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_variant_id", UUID(as_uuid=True),
            sa.ForeignKey("catalog.product_variants.id", ondelete="NO ACTION"),
            nullable=False,
        ),
        sa.Column("quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("selling_price", sa.Numeric(14, 2), nullable=False),
        sa.Column("unit_cost", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("tax_rate", sa.Numeric(6, 4), nullable=False, server_default="0"),
        sa.Column("discount_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("total_line_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("bill_id", "product_variant_id", name="uq_sales_lines_bill_variant"),
        schema="sales",
    )
    op.create_index("ix_sales_lines_bill", "sale_bill_lines", ["bill_id"], schema="sales")
    op.create_index("ix_sales_lines_variant", "sale_bill_lines", ["product_variant_id"], schema="sales")

    # 4. sales.sale_payments
    op.create_table(
        "sale_payments",
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
            sa.ForeignKey("sales.sale_bills.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("payment_date", sa.Date, nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("payment_mode", sa.String(20), nullable=False),
        sa.Column("transaction_id", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        schema="sales",
    )
    op.create_index("ix_sales_payments_bill", "sale_payments", ["bill_id"], schema="sales")
    op.create_index("ix_sales_payments_tenant", "sale_payments", ["tenant_id"], schema="sales")


def downgrade() -> None:
    op.drop_table("sale_payments", schema="sales")
    op.drop_table("sale_bill_lines", schema="sales")
    op.drop_table("sale_bills", schema="sales")
    op.drop_table("customers", schema="sales")
    op.execute("DROP SCHEMA IF EXISTS sales")
