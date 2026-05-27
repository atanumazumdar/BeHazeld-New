"""Initial schema — add collections, product_images, product_variants;
refactor products table; add variant_id to order_items.

Revision ID: 0001
Revises:
Create Date: 2026-05-15

Strategy (SQLite-safe):
  1. Create new tables (collections, product_images, product_variants)
  2. Add new nullable columns to products via batch_alter_table
  3. Data migration: populate collections → products → images → variants
  4. Make base_price / is_active NOT NULL after population
  5. Drop stale columns from products via batch_alter_table
  6. Add variant_id to order_items
"""

from __future__ import annotations

import re
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ── Canonical collections in display order ───────────────────────────
COLLECTIONS = [
    ("Campus Muse",       "campus-muse",       "Effortless. Expressive. Unapologetically You.",  "/campus-muse-new.png",        1),
    ("Power Edit",        "power-edit",         "Tailored for ambition. Styled for impact.",       "/power-edit.png",             2),
    ("Afterglow Evenings","afterglow-evenings", "Turn moments into statements.",                   "/afterglow-evenings-new.png", 3),
    ("Ultra Luxe",        "ultra-luxe",         "For the woman who commands every room.",          None,                          4),
    ("Accessories",       "accessories",        "The finishing touch that defines the look.",      None,                          5),
    ("Pre Loved",         "pre-loved",          "Sustainably yours. Uniquely Hazel.",              None,                          6),
]

# Map existing product slugs → collection slug
PRODUCT_COLLECTION_MAP = {
    "ivory-bloom-lehenga":    "campus-muse",
    "antique-gold-anarkali":  "power-edit",
    "heritage-kanjivaram-saree": "afterglow-evenings",
    "champagne-zari-set":     "afterglow-evenings",
}


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


# ════════════════════════════════════════════════════════════════════
# UPGRADE
# ════════════════════════════════════════════════════════════════════
def upgrade() -> None:
    conn = op.get_bind()

    # ── 1. Create collections ────────────────────────────────────────
    op.create_table(
        "collections",
        sa.Column("id",            sa.Integer(),     primary_key=True),
        sa.Column("name",          sa.String(120),   nullable=False),
        sa.Column("slug",          sa.String(140),   nullable=False, unique=True),
        sa.Column("description",   sa.Text(),        nullable=False, server_default=""),
        sa.Column("hero_image_url",sa.String(500),   nullable=True),
        sa.Column("display_order", sa.Integer(),     nullable=False, server_default="0"),
        sa.Column("is_active",     sa.Boolean(),     nullable=False, server_default="1"),
        sa.Column("created_at",    sa.DateTime(),    nullable=False,
                  server_default=sa.func.current_timestamp()),
    )
    op.create_index("ix_collections_slug", "collections", ["slug"], unique=True)

    # ── 2. Create product_images ─────────────────────────────────────
    op.create_table(
        "product_images",
        sa.Column("id",            sa.Integer(),     primary_key=True),
        sa.Column("product_id",    sa.Integer(),     sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url",           sa.String(600),   nullable=False),
        sa.Column("alt_text",      sa.String(220),   nullable=False, server_default=""),
        sa.Column("display_order", sa.Integer(),     nullable=False, server_default="0"),
        sa.Column("is_primary",    sa.Boolean(),     nullable=False, server_default="0"),
    )
    op.create_index("ix_product_images_product_id", "product_images", ["product_id"])

    # ── 3. Create product_variants ───────────────────────────────────
    op.create_table(
        "product_variants",
        sa.Column("id",               sa.Integer(),      primary_key=True),
        sa.Column("product_id",       sa.Integer(),      sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sku",              sa.String(80),     nullable=False, unique=True),
        sa.Column("color",            sa.String(60),     nullable=False),
        sa.Column("size",             sa.String(40),     nullable=False),
        sa.Column("price_adjustment", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("stock_count",      sa.Integer(),      nullable=False, server_default="0"),
        sa.Column("is_available",     sa.Boolean(),      nullable=False, server_default="1"),
    )
    op.create_index("ix_product_variants_product_id", "product_variants", ["product_id"])
    op.create_index("ix_product_variants_sku",        "product_variants", ["sku"], unique=True)
    op.create_unique_constraint(
        "uq_variant_product_color_size",
        "product_variants",
        ["product_id", "color", "size"],
    )

    # ── 4. Add new columns to products (all nullable first) ──────────
    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.add_column(sa.Column("collection_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("base_price",    sa.Numeric(10, 2), nullable=True))
        batch_op.add_column(sa.Column("is_active",     sa.Boolean(),      nullable=True,
                                      server_default="1"))

    # ── 5. DATA MIGRATION ────────────────────────────────────────────

    # 5a. Insert collections
    for name, slug, description, hero_url, order in COLLECTIONS:
        conn.execute(
            sa.text(
                "INSERT INTO collections (name, slug, description, hero_image_url, "
                "display_order, is_active) VALUES (:n, :s, :d, :h, :o, 1)"
            ),
            {"n": name, "s": slug, "d": description, "h": hero_url, "o": order},
        )

    # 5b. Build slug → id map
    coll_rows = conn.execute(
        sa.text("SELECT id, slug FROM collections")
    ).fetchall()
    coll_id_by_slug = {row[1]: row[0] for row in coll_rows}

    # 5c. Load existing products
    products = conn.execute(
        sa.text(
            "SELECT id, name, slug, price, image_url, color, size, inventory_count "
            "FROM products"
        )
    ).fetchall()

    for prod in products:
        prod_id, name, slug, price, image_url, color, size, stock = prod

        # Assign collection
        coll_slug = PRODUCT_COLLECTION_MAP.get(slug, "campus-muse")
        coll_id   = coll_id_by_slug.get(coll_slug)

        # Populate new columns
        conn.execute(
            sa.text(
                "UPDATE products SET base_price=:bp, collection_id=:ci, is_active=1 "
                "WHERE id=:id"
            ),
            {"bp": price, "ci": coll_id, "id": prod_id},
        )

        # Create primary product image
        alt = name
        conn.execute(
            sa.text(
                "INSERT INTO product_images "
                "(product_id, url, alt_text, display_order, is_primary) "
                "VALUES (:pid, :url, :alt, 0, 1)"
            ),
            {"pid": prod_id, "url": image_url, "alt": alt},
        )

        # Create default variant from existing color / size / stock
        # SKU format: BH-<SLUG_PREFIX>-<COLOR_CODE>-001
        slug_prefix  = slug.replace("-", "")[:10].upper()
        color_code   = re.sub(r"[^A-Z]", "", color.upper())[:3] or "CLR"
        sku          = f"BH-{slug_prefix}-{color_code}-001"

        conn.execute(
            sa.text(
                "INSERT INTO product_variants "
                "(product_id, sku, color, size, price_adjustment, stock_count, is_available) "
                "VALUES (:pid, :sku, :color, :size, 0.00, :stock, 1)"
            ),
            {"pid": prod_id, "sku": sku, "color": color, "size": size, "stock": stock},
        )

    # ── 6. Drop stale columns from products (batch for SQLite) ───────
    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.drop_column("category")
        batch_op.drop_column("image_url")
        batch_op.drop_column("color")
        batch_op.drop_column("size")
        batch_op.drop_column("inventory_count")
        batch_op.drop_column("price")
        # Create FK index now that data is in place
        batch_op.create_index("ix_products_collection_id", ["collection_id"])

    # ── 7. Add variant_id to order_items ─────────────────────────────
    with op.batch_alter_table("order_items", schema=None) as batch_op:
        batch_op.add_column(sa.Column("variant_id", sa.Integer(), nullable=True))


# ════════════════════════════════════════════════════════════════════
# DOWNGRADE  (reverses the migration — restores old schema)
# ════════════════════════════════════════════════════════════════════
def downgrade() -> None:
    # Restore stale columns to products
    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.drop_index("ix_products_collection_id")
        batch_op.add_column(sa.Column("price",           sa.Numeric(10, 2), nullable=True))
        batch_op.add_column(sa.Column("inventory_count", sa.Integer(),      nullable=True, server_default="0"))
        batch_op.add_column(sa.Column("size",            sa.String(40),     nullable=True, server_default=""))
        batch_op.add_column(sa.Column("color",           sa.String(60),     nullable=True, server_default=""))
        batch_op.add_column(sa.Column("image_url",       sa.String(500),    nullable=True, server_default=""))
        batch_op.add_column(sa.Column("category",        sa.String(80),     nullable=True, server_default=""))
        batch_op.drop_column("is_active")
        batch_op.drop_column("base_price")
        batch_op.drop_column("collection_id")

    # Remove variant_id from order_items
    with op.batch_alter_table("order_items", schema=None) as batch_op:
        batch_op.drop_column("variant_id")

    op.drop_table("product_variants")
    op.drop_table("product_images")
    op.drop_table("collections")
