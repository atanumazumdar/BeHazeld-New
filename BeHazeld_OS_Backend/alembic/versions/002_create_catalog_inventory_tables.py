"""create catalog and inventory schemas and all Phase 2 tables

Revision ID: 002
Revises: 001
Create Date: 2026-05-25

Tables created (13 total, in FK-dependency order):

  catalog schema  (9 tables)
  ─────────────────────────────────────────────────────
  1.  catalog.product_categories   ← no FK deps inside catalog
  2.  catalog.product_groups        ← no FK deps inside catalog
  3.  catalog.product_types         ← no FK deps inside catalog
  4.  catalog.brands                ← no FK deps inside catalog
  5.  catalog.sizes                 ← no FK deps inside catalog
  6.  catalog.colors                ← no FK deps inside catalog
  7.  catalog.products              ← FKs → categories, groups, types, brands
  8.  catalog.product_variants      ← FKs → products, sizes, colors
  9.  catalog.barcodes              ← FK  → product_variants

  inventory schema  (4 tables)
  ─────────────────────────────────────────────────────
  10. inventory.bins                ← FK  → tenant.locations
  11. inventory.stock_batches       ← FKs → product_variants, bins
  12. inventory.stock_ledger        ← FKs → product_variants, bins, stock_batches
  13. inventory.stock_balances      ← FKs → product_variants, bins
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_schemas() -> None:
    """Create PostgreSQL schemas idempotently."""
    op.execute("CREATE SCHEMA IF NOT EXISTS catalog")
    op.execute("CREATE SCHEMA IF NOT EXISTS inventory")


def upgrade() -> None:
    _create_schemas()

    # ══════════════════════════════════════════════════════════════════════════
    # CATALOG SCHEMA — master tables first (no inter-catalog FK dependencies)
    # ══════════════════════════════════════════════════════════════════════════

    # 1. catalog.product_categories
    op.create_table(
        "product_categories",
        sa.Column(
            "id", UUID(as_uuid=True),
            primary_key=True, server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id", UUID(as_uuid=True),
            sa.ForeignKey("tenant.tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "tenant_id", "name", name="uq_catalog_categories_tenant_name"
        ),
        schema="catalog",
    )
    op.create_index(
        "ix_catalog_categories_tenant",
        "product_categories", ["tenant_id"], schema="catalog",
    )

    # 2. catalog.product_groups
    op.create_table(
        "product_groups",
        sa.Column(
            "id", UUID(as_uuid=True),
            primary_key=True, server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id", UUID(as_uuid=True),
            sa.ForeignKey("tenant.tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "tenant_id", "name", name="uq_catalog_groups_tenant_name"
        ),
        schema="catalog",
    )
    op.create_index(
        "ix_catalog_groups_tenant",
        "product_groups", ["tenant_id"], schema="catalog",
    )

    # 3. catalog.product_types
    op.create_table(
        "product_types",
        sa.Column(
            "id", UUID(as_uuid=True),
            primary_key=True, server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id", UUID(as_uuid=True),
            sa.ForeignKey("tenant.tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "tenant_id", "name", name="uq_catalog_types_tenant_name"
        ),
        schema="catalog",
    )
    op.create_index(
        "ix_catalog_types_tenant",
        "product_types", ["tenant_id"], schema="catalog",
    )

    # 4. catalog.brands
    op.create_table(
        "brands",
        sa.Column(
            "id", UUID(as_uuid=True),
            primary_key=True, server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id", UUID(as_uuid=True),
            sa.ForeignKey("tenant.tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "tenant_id", "name", name="uq_catalog_brands_tenant_name"
        ),
        schema="catalog",
    )
    op.create_index(
        "ix_catalog_brands_tenant",
        "brands", ["tenant_id"], schema="catalog",
    )

    # 5. catalog.sizes
    op.create_table(
        "sizes",
        sa.Column(
            "id", UUID(as_uuid=True),
            primary_key=True, server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id", UUID(as_uuid=True),
            sa.ForeignKey("tenant.tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "tenant_id", "name", name="uq_catalog_sizes_tenant_name"
        ),
        schema="catalog",
    )
    op.create_index(
        "ix_catalog_sizes_tenant",
        "sizes", ["tenant_id"], schema="catalog",
    )

    # 6. catalog.colors
    op.create_table(
        "colors",
        sa.Column(
            "id", UUID(as_uuid=True),
            primary_key=True, server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id", UUID(as_uuid=True),
            sa.ForeignKey("tenant.tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("hex_code", sa.String(7), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "tenant_id", "name", name="uq_catalog_colors_tenant_name"
        ),
        schema="catalog",
    )
    op.create_index(
        "ix_catalog_colors_tenant",
        "colors", ["tenant_id"], schema="catalog",
    )

    # 7. catalog.products — depends on all 6 master tables above
    op.create_table(
        "products",
        sa.Column(
            "id", UUID(as_uuid=True),
            primary_key=True, server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id", UUID(as_uuid=True),
            sa.ForeignKey("tenant.tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # All master FKs are nullable — products can be created before masters
        sa.Column(
            "category_id", UUID(as_uuid=True),
            sa.ForeignKey("catalog.product_categories.id", ondelete="NO ACTION"),
            nullable=True,
        ),
        sa.Column(
            "product_group_id", UUID(as_uuid=True),
            sa.ForeignKey("catalog.product_groups.id", ondelete="NO ACTION"),
            nullable=True,
        ),
        sa.Column(
            "product_type_id", UUID(as_uuid=True),
            sa.ForeignKey("catalog.product_types.id", ondelete="NO ACTION"),
            nullable=True,
        ),
        sa.Column(
            "brand_id", UUID(as_uuid=True),
            sa.ForeignKey("catalog.brands.id", ondelete="NO ACTION"),
            nullable=True,
        ),
        sa.Column("product_code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(250), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default="active"
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "tenant_id", "product_code", name="uq_catalog_products_tenant_code"
        ),
        schema="catalog",
    )
    op.create_index(
        "ix_catalog_products_tenant_status",
        "products", ["tenant_id", "status"], schema="catalog",
    )

    # 8. catalog.product_variants — depends on products, sizes, colors
    op.create_table(
        "product_variants",
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
            "product_id", UUID(as_uuid=True),
            sa.ForeignKey("catalog.products.id", ondelete="NO ACTION"),
            nullable=False,
        ),
        sa.Column(
            "size_id", UUID(as_uuid=True),
            sa.ForeignKey("catalog.sizes.id", ondelete="NO ACTION"),
            nullable=False,
        ),
        sa.Column(
            "color_id", UUID(as_uuid=True),
            sa.ForeignKey("catalog.colors.id", ondelete="NO ACTION"),
            nullable=False,
        ),
        sa.Column("sku_code", sa.String(100), nullable=False),
        sa.Column("fabric", sa.String(150), nullable=True),
        sa.Column("mrp", sa.Numeric(12, 4), nullable=False),
        sa.Column("selling_price", sa.Numeric(12, 4), nullable=False),
        sa.Column("cost_price", sa.Numeric(12, 4), nullable=False),
        sa.Column("reorder_level", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default="active"
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "tenant_id", "sku_code", name="uq_catalog_variants_tenant_sku"
        ),
        schema="catalog",
    )
    op.create_index(
        "ix_catalog_variants_product",
        "product_variants", ["product_id"], schema="catalog",
    )
    op.create_index(
        "ix_catalog_variants_tenant_status",
        "product_variants", ["tenant_id", "status"], schema="catalog",
    )

    # 9. catalog.barcodes — depends on product_variants
    op.create_table(
        "barcodes",
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
            "variant_id", UUID(as_uuid=True),
            sa.ForeignKey("catalog.product_variants.id", ondelete="NO ACTION"),
            nullable=False,
        ),
        sa.Column("value", sa.String(150), nullable=False),
        sa.Column(
            "barcode_type", sa.String(30), nullable=False, server_default="EAN13"
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "tenant_id", "value", name="uq_catalog_barcodes_tenant_value"
        ),
        schema="catalog",
    )
    op.create_index(
        "ix_catalog_barcodes_variant",
        "barcodes", ["variant_id"], schema="catalog",
    )

    # ══════════════════════════════════════════════════════════════════════════
    # INVENTORY SCHEMA — bins must exist before batches, ledger, and balances
    # ══════════════════════════════════════════════════════════════════════════

    # 10. inventory.bins — depends on tenant.locations only
    op.create_table(
        "bins",
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
            "location_id", UUID(as_uuid=True),
            sa.ForeignKey("tenant.locations.id", ondelete="NO ACTION"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.UniqueConstraint(
            "location_id", "name", name="uq_inventory_bins_location_name"
        ),
        schema="inventory",
    )
    op.create_index(
        "ix_inventory_bins_tenant",
        "bins", ["tenant_id"], schema="inventory",
    )
    op.create_index(
        "ix_inventory_bins_location",
        "bins", ["location_id"], schema="inventory",
    )

    # 11. inventory.stock_batches — depends on catalog.product_variants + inventory.bins
    op.create_table(
        "stock_batches",
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
            "product_variant_id", UUID(as_uuid=True),
            sa.ForeignKey("catalog.product_variants.id", ondelete="NO ACTION"),
            nullable=False,
        ),
        sa.Column(
            "location_id", UUID(as_uuid=True),
            sa.ForeignKey("tenant.locations.id", ondelete="NO ACTION"),
            nullable=False,
        ),
        sa.Column(
            "bin_id", UUID(as_uuid=True),
            sa.ForeignKey("inventory.bins.id", ondelete="NO ACTION"),
            nullable=False,   # NOT NULL — prevents phantom-duplicate balances
        ),
        sa.Column("batch_number", sa.String(100), nullable=False),
        sa.Column("initial_quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("remaining_quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("unit_cost", sa.Numeric(12, 4), nullable=False),
        sa.Column("purchase_bill_ref", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.UniqueConstraint(
            "tenant_id", "batch_number", name="uq_inventory_batches_tenant_number"
        ),
        schema="inventory",
    )
    op.create_index(
        "ix_inventory_batches_tenant_variant",
        "stock_batches", ["tenant_id", "product_variant_id"], schema="inventory",
    )

    # 12. inventory.stock_ledger — depends on product_variants, bins, stock_batches
    op.create_table(
        "stock_ledger",
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
            "product_variant_id", UUID(as_uuid=True),
            sa.ForeignKey("catalog.product_variants.id", ondelete="NO ACTION"),
            nullable=False,
        ),
        sa.Column(
            "location_id", UUID(as_uuid=True),
            sa.ForeignKey("tenant.locations.id", ondelete="NO ACTION"),
            nullable=False,
        ),
        sa.Column(
            "bin_id", UUID(as_uuid=True),
            sa.ForeignKey("inventory.bins.id", ondelete="NO ACTION"),
            nullable=False,   # NOT NULL — every movement must reference a bin
        ),
        sa.Column(
            "batch_id", UUID(as_uuid=True),
            sa.ForeignKey("inventory.stock_batches.id", ondelete="NO ACTION"),
            nullable=True,    # NULL for opening stock (no source batch)
        ),
        sa.Column("movement_type", sa.String(30), nullable=False),
        sa.Column("quantity_change", sa.Numeric(14, 4), nullable=False),
        sa.Column("unit_cost", sa.Numeric(12, 4), nullable=False),
        sa.Column("reference_type", sa.String(50), nullable=True),
        sa.Column("reference_id", UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "performed_by_user_id", UUID(as_uuid=True),
            sa.ForeignKey("identity.users.id", ondelete="NO ACTION"),
            nullable=True,
        ),
        schema="inventory",
    )
    op.create_index(
        "ix_inventory_ledger_tenant_variant_location",
        "stock_ledger",
        ["tenant_id", "product_variant_id", "location_id"],
        schema="inventory",
    )
    op.create_index(
        "ix_inventory_ledger_reference",
        "stock_ledger", ["reference_type", "reference_id"], schema="inventory",
    )

    # 13. inventory.stock_balances — depends on product_variants + bins
    #     Four-column composite unique constraint works reliably because bin_id
    #     is NOT NULL (fixes the Supabase phantom-duplicate bug).
    op.create_table(
        "stock_balances",
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
            "product_variant_id", UUID(as_uuid=True),
            sa.ForeignKey("catalog.product_variants.id", ondelete="NO ACTION"),
            nullable=False,
        ),
        sa.Column(
            "location_id", UUID(as_uuid=True),
            sa.ForeignKey("tenant.locations.id", ondelete="NO ACTION"),
            nullable=False,
        ),
        sa.Column(
            "bin_id", UUID(as_uuid=True),
            sa.ForeignKey("inventory.bins.id", ondelete="NO ACTION"),
            nullable=False,   # NOT NULL — makes composite unique constraint reliable
        ),
        sa.Column(
            "quantity_on_hand", sa.Numeric(14, 4),
            nullable=False, server_default="0",
        ),
        sa.Column(
            "quantity_reserved", sa.Numeric(14, 4),
            nullable=False, server_default="0",
        ),
        sa.UniqueConstraint(
            "tenant_id", "product_variant_id", "location_id", "bin_id",
            name="uq_inventory_balance_variant_location_bin",
        ),
        schema="inventory",
    )
    op.create_index(
        "ix_inventory_balance_tenant_variant",
        "stock_balances", ["tenant_id", "product_variant_id"], schema="inventory",
    )


def downgrade() -> None:
    """
    Drop all Phase 2 tables in strict reverse FK-dependency order.

    Inventory tables reference catalog tables, so inventory must come out first.
    Within each schema, tables with outbound FKs are dropped before the tables
    they reference.

    Schemas are intentionally left in place — dropping a non-empty schema
    requires emptying it first and is a destructive manual operation.
    """
    # ── inventory (reverse of creation order) ────────────────────────────────
    op.drop_index("ix_inventory_balance_tenant_variant", "stock_balances", schema="inventory")
    op.drop_table("stock_balances", schema="inventory")

    op.drop_index("ix_inventory_ledger_reference", "stock_ledger", schema="inventory")
    op.drop_index("ix_inventory_ledger_tenant_variant_location", "stock_ledger", schema="inventory")
    op.drop_table("stock_ledger", schema="inventory")

    op.drop_index("ix_inventory_batches_tenant_variant", "stock_batches", schema="inventory")
    op.drop_table("stock_batches", schema="inventory")

    op.drop_index("ix_inventory_bins_location", "bins", schema="inventory")
    op.drop_index("ix_inventory_bins_tenant", "bins", schema="inventory")
    op.drop_table("bins", schema="inventory")

    # ── catalog (reverse of creation order) ──────────────────────────────────
    op.drop_index("ix_catalog_barcodes_variant", "barcodes", schema="catalog")
    op.drop_table("barcodes", schema="catalog")

    op.drop_index("ix_catalog_variants_tenant_status", "product_variants", schema="catalog")
    op.drop_index("ix_catalog_variants_product", "product_variants", schema="catalog")
    op.drop_table("product_variants", schema="catalog")

    op.drop_index("ix_catalog_products_tenant_status", "products", schema="catalog")
    op.drop_table("products", schema="catalog")

    op.drop_index("ix_catalog_colors_tenant", "colors", schema="catalog")
    op.drop_table("colors", schema="catalog")

    op.drop_index("ix_catalog_sizes_tenant", "sizes", schema="catalog")
    op.drop_table("sizes", schema="catalog")

    op.drop_index("ix_catalog_brands_tenant", "brands", schema="catalog")
    op.drop_table("brands", schema="catalog")

    op.drop_index("ix_catalog_types_tenant", "product_types", schema="catalog")
    op.drop_table("product_types", schema="catalog")

    op.drop_index("ix_catalog_groups_tenant", "product_groups", schema="catalog")
    op.drop_table("product_groups", schema="catalog")

    op.drop_index("ix_catalog_categories_tenant", "product_categories", schema="catalog")
    op.drop_table("product_categories", schema="catalog")
