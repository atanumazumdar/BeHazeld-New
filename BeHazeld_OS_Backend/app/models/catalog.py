"""
Catalog domain models.

Hierarchy:
  Category    ─┐
  ProductGroup ─┤
  ProductType  ─┼──► Product ──► ProductVariant (SKU) ──► Barcode
  Brand        ─┤
  Size / Color ─┘

Design decisions
----------------
* All PKs use PostgreSQL UUID columns; the ORM generates UUIDs for writes.
* Every table has tenant_id — all queries must filter by it.
* `status` fields use VARCHAR("active"|"deleted") for soft-delete; VARCHAR
  avoids painful migrations on enum changes.
* Optional FK references on Product (category, group, type, brand) allow
  products to be created before all master records are configured.
* `generate_product_code` and `generate_sku_code` live in the repository
  module (not here) — they need access to DB counts and are tested there.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

_SCHEMA = "catalog"
_PRICE = Numeric(12, 4)   # INR amounts up to 99,999,999.9999


# ── Master / lookup tables ────────────────────────────────────────────────────

class Category(Base, TimestampMixin):
    """Top-level garment category — e.g. Men's Wear, Women's Wear, Kids."""

    __tablename__ = "product_categories"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_catalog_categories_tenant_name"),
        Index("ix_catalog_categories_tenant", "tenant_id"),
        {"schema": _SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")

    products: Mapped[list[Product]] = relationship(back_populates="category")


class ProductGroup(Base, TimestampMixin):
    """
    Collection / product group — replaces the free-text `collection` column
    from the Supabase design.  Being a proper master record enables consistent
    product-code generation from the group name prefix.
    """

    __tablename__ = "product_groups"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_catalog_groups_tenant_name"),
        Index("ix_catalog_groups_tenant", "tenant_id"),
        {"schema": _SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")

    products: Mapped[list[Product]] = relationship(back_populates="product_group")


class ProductType(Base, TimestampMixin):
    """Garment type — e.g. T-Shirt, Jeans, Kurti, Dress."""

    __tablename__ = "product_types"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_catalog_types_tenant_name"),
        Index("ix_catalog_types_tenant", "tenant_id"),
        {"schema": _SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")

    products: Mapped[list[Product]] = relationship(back_populates="product_type")


class Brand(Base, TimestampMixin):
    """Brand master — e.g. BeHazel'd, own-label sub-brands."""

    __tablename__ = "brands"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_catalog_brands_tenant_name"),
        Index("ix_catalog_brands_tenant", "tenant_id"),
        {"schema": _SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")

    products: Mapped[list[Product]] = relationship(back_populates="brand")


class Size(Base, TimestampMixin):
    """
    Size master — XS/S/M/L/XL/XXL or numeric (28/30/32).
    `sort_order` controls display order in size dropdowns.
    """

    __tablename__ = "sizes"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_catalog_sizes_tenant_name"),
        Index("ix_catalog_sizes_tenant", "tenant_id"),
        {"schema": _SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")

    variants: Mapped[list[ProductVariant]] = relationship(back_populates="size")


class Color(Base, TimestampMixin):
    """Color master — name + optional hex code for UI swatches."""

    __tablename__ = "colors"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_catalog_colors_tenant_name"),
        Index("ix_catalog_colors_tenant", "tenant_id"),
        {"schema": _SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    hex_code: Mapped[str | None] = mapped_column(String(7))   # e.g. "#FF5733"
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")

    variants: Mapped[list[ProductVariant]] = relationship(back_populates="color")


# ── Product ───────────────────────────────────────────────────────────────────

class Product(Base, TimestampMixin):
    """
    A physical product — parent of all SKUs (ProductVariants).

    `product_code` is unique per tenant and auto-generated by the service layer
    using `generate_product_code()` from catalog_repository when not explicitly
    provided. The repository's `create_product()` always requires an explicit
    product_code — generation is a service-layer concern.

    Optional FK references (category, product_group, product_type, brand) allow
    a product to be created before all master data is configured.

    `status`: "active" | "deleted"  (soft-delete).
    """

    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("tenant_id", "product_code", name="uq_catalog_products_tenant_code"),
        Index("ix_catalog_products_tenant_status", "tenant_id", "status"),
        {"schema": _SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_SCHEMA}.product_categories.id", ondelete="NO ACTION"),
    )
    product_group_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_SCHEMA}.product_groups.id", ondelete="NO ACTION"),
    )
    product_type_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_SCHEMA}.product_types.id", ondelete="NO ACTION"),
    )
    brand_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_SCHEMA}.brands.id", ondelete="NO ACTION"),
    )

    product_code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", server_default="active"
    )

    category: Mapped[Category | None] = relationship(back_populates="products")
    product_group: Mapped[ProductGroup | None] = relationship(back_populates="products")
    product_type: Mapped[ProductType | None] = relationship(back_populates="products")
    brand: Mapped[Brand | None] = relationship(back_populates="products")
    variants: Mapped[list[ProductVariant]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Product code={self.product_code!r} name={self.name!r}>"


# ── ProductVariant (SKU) ──────────────────────────────────────────────────────

class ProductVariant(Base, TimestampMixin):
    """
    A single purchasable SKU — one specific size + color + fabric combination.

    Pricing columns:
      mrp           — Maximum Retail Price (printed on tag / legal requirement)
      selling_price — actual price charged to customer
      cost_price    — landed cost (used for COGS / gross-profit calculation)

    `sku_code` is unique per tenant; the service layer calls `generate_sku_code()`
    before calling `create_variant()`.
    `status`: "active" | "deleted"  (soft-delete).
    """

    __tablename__ = "product_variants"
    __table_args__ = (
        UniqueConstraint("tenant_id", "sku_code", name="uq_catalog_variants_tenant_sku"),
        Index("ix_catalog_variants_product", "product_id"),
        Index("ix_catalog_variants_tenant_status", "tenant_id", "status"),
        {"schema": _SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_SCHEMA}.products.id", ondelete="NO ACTION"),
        nullable=False,
    )
    size_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_SCHEMA}.sizes.id", ondelete="NO ACTION"),
        nullable=False,
    )
    color_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_SCHEMA}.colors.id", ondelete="NO ACTION"),
        nullable=False,
    )

    sku_code: Mapped[str] = mapped_column(String(100), nullable=False)
    fabric: Mapped[str | None] = mapped_column(String(150))   # free-text, no master needed
    image_url: Mapped[str | None] = mapped_column(String(500))

    mrp: Mapped[Decimal] = mapped_column(_PRICE, nullable=False)
    selling_price: Mapped[Decimal] = mapped_column(_PRICE, nullable=False)
    cost_price: Mapped[Decimal] = mapped_column(_PRICE, nullable=False)

    reorder_level: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", server_default="active"
    )

    product: Mapped[Product] = relationship(back_populates="variants")
    size: Mapped[Size] = relationship(back_populates="variants")
    color: Mapped[Color] = relationship(back_populates="variants")
    barcodes: Mapped[list[Barcode]] = relationship(
        back_populates="variant", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ProductVariant sku={self.sku_code!r}>"


# ── Barcode ───────────────────────────────────────────────────────────────────

class Barcode(Base, TimestampMixin):
    """
    Barcode or RFID tag attached to a ProductVariant.
    A single variant can carry multiple barcodes (EAN-13, QR, RFID, INTERNAL).
    `value` is unique per tenant to prevent cross-variant scanning collisions.
    """

    __tablename__ = "barcodes"
    __table_args__ = (
        UniqueConstraint("tenant_id", "value", name="uq_catalog_barcodes_tenant_value"),
        Index("ix_catalog_barcodes_variant", "variant_id"),
        {"schema": _SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{_SCHEMA}.product_variants.id", ondelete="NO ACTION"),
        nullable=False,
    )
    value: Mapped[str] = mapped_column(String(150), nullable=False)
    barcode_type: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="EAN13"
    )   # EAN13 | QR | RFID | INTERNAL

    variant: Mapped[ProductVariant] = relationship(back_populates="barcodes")
