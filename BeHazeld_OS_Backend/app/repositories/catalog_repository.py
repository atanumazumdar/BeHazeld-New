"""
Catalog repository — pure data access layer for the catalog schema.

Rule: every read method receives tenant_id as its first argument and uses it
as the primary WHERE filter. This is the only place in the codebase where raw
SQLAlchemy queries for catalog data are written.

Module-level helpers
--------------------
generate_product_code(group_name, product_name, seq) → str
    Pure function — deterministic, no DB calls. Called by the service layer,
    which calls count_products_by_tenant() to get the sequence number.

generate_sku_code(product_code, size_name, color_name) → str
    Pure function — deterministic, no DB calls.
"""
import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.catalog import (
    Barcode,
    Brand,
    Category,
    Color,
    Product,
    ProductGroup,
    ProductType,
    ProductVariant,
    Size,
)


# ── Pure helpers — used by service layer for code generation ──────────────────

def generate_product_code(group_name: str, product_name: str, seq: int) -> str:
    """
    Produce a human-readable, unique product code.

    Format: {GROUP[:3]}-{NAME[:4]}-{SEQ:04d}
    Examples:
      ("Summer Collection", "Kurti", 1)  → "SUM-KURT-0001"
      ("Winter",            "Jacket", 42) → "WIN-JACK-0042"
      ("Go",                "T",      1)  → "GO-T-0001"
    """
    g = group_name.strip().upper().replace(" ", "")[:3]
    n = product_name.strip().upper().replace(" ", "")[:4]
    return f"{g}-{n}-{seq:04d}"


def generate_sku_code(product_code: str, size_name: str, color_name: str) -> str:
    """
    Append size+color suffixes to the product code to form the SKU.

    Format: {product_code}-{SIZE[:2]}{COLOR[:3]}  (all upper-case, no spaces)
    Examples:
      ("SUM-KURT-0001", "XL",  "Midnight Blue") → "SUM-KURT-0001-XLMID"
      ("WIN-JACK-0042", "S",   "Red")            → "WIN-JACK-0042-SRED"
    """
    s = size_name.strip().upper().replace(" ", "")[:2]
    c = color_name.strip().upper().replace(" ", "")[:3]
    return f"{product_code}-{s}{c}"


# ── Repository ────────────────────────────────────────────────────────────────

class CatalogRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ── master table reads ────────────────────────────────────────────────────

    def list_categories(self, tenant_id: uuid.UUID) -> list[Category]:
        return list(
            self.db.scalars(
                select(Category)
                .where(Category.tenant_id == tenant_id, Category.is_active.is_(True))
                .order_by(Category.sort_order, Category.name)
            )
        )

    def list_product_groups(self, tenant_id: uuid.UUID) -> list[ProductGroup]:
        return list(
            self.db.scalars(
                select(ProductGroup)
                .where(ProductGroup.tenant_id == tenant_id, ProductGroup.is_active.is_(True))
                .order_by(ProductGroup.name)
            )
        )

    def list_product_types(self, tenant_id: uuid.UUID) -> list[ProductType]:
        return list(
            self.db.scalars(
                select(ProductType)
                .where(ProductType.tenant_id == tenant_id, ProductType.is_active.is_(True))
                .order_by(ProductType.name)
            )
        )

    def list_brands(self, tenant_id: uuid.UUID) -> list[Brand]:
        return list(
            self.db.scalars(
                select(Brand)
                .where(Brand.tenant_id == tenant_id, Brand.is_active.is_(True))
                .order_by(Brand.name)
            )
        )

    def list_sizes(self, tenant_id: uuid.UUID) -> list[Size]:
        return list(
            self.db.scalars(
                select(Size)
                .where(Size.tenant_id == tenant_id, Size.is_active.is_(True))
                .order_by(Size.sort_order, Size.name)
            )
        )

    def list_colors(self, tenant_id: uuid.UUID) -> list[Color]:
        return list(
            self.db.scalars(
                select(Color)
                .where(Color.tenant_id == tenant_id, Color.is_active.is_(True))
                .order_by(Color.name)
            )
        )

    # ── master creates ────────────────────────────────────────────────────────

    def create_category(
        self,
        tenant_id: uuid.UUID,
        name: str,
        description: str | None = None,
        sort_order: int = 0,
    ) -> Category:
        obj = Category(
            tenant_id=tenant_id, name=name, description=description,
            sort_order=sort_order, is_active=True,
        )
        self.db.add(obj)
        self.db.flush()
        return obj

    def create_product_group(
        self,
        tenant_id: uuid.UUID,
        name: str,
        description: str | None = None,
    ) -> ProductGroup:
        obj = ProductGroup(
            tenant_id=tenant_id, name=name, description=description, is_active=True,
        )
        self.db.add(obj)
        self.db.flush()
        return obj

    def get_product_group_by_id(
        self, tenant_id: uuid.UUID, group_id: uuid.UUID
    ) -> ProductGroup | None:
        return self.db.scalar(
            select(ProductGroup).where(
                ProductGroup.tenant_id == tenant_id,
                ProductGroup.id == group_id,
            )
        )

    def create_product_type(self, tenant_id: uuid.UUID, name: str) -> ProductType:
        obj = ProductType(tenant_id=tenant_id, name=name, is_active=True)
        self.db.add(obj)
        self.db.flush()
        return obj

    def create_brand(self, tenant_id: uuid.UUID, name: str) -> Brand:
        obj = Brand(tenant_id=tenant_id, name=name, is_active=True)
        self.db.add(obj)
        self.db.flush()
        return obj

    def create_size(
        self, tenant_id: uuid.UUID, name: str, sort_order: int = 0
    ) -> Size:
        obj = Size(tenant_id=tenant_id, name=name, sort_order=sort_order, is_active=True)
        self.db.add(obj)
        self.db.flush()
        return obj

    def create_color(
        self, tenant_id: uuid.UUID, name: str, hex_code: str | None = None
    ) -> Color:
        obj = Color(tenant_id=tenant_id, name=name, hex_code=hex_code, is_active=True)
        self.db.add(obj)
        self.db.flush()
        return obj

    def get_size_by_id(self, tenant_id: uuid.UUID, size_id: uuid.UUID) -> Size | None:
        return self.db.scalar(
            select(Size).where(Size.tenant_id == tenant_id, Size.id == size_id)
        )

    def get_color_by_id(self, tenant_id: uuid.UUID, color_id: uuid.UUID) -> Color | None:
        return self.db.scalar(
            select(Color).where(Color.tenant_id == tenant_id, Color.id == color_id)
        )

    # ── product reads ─────────────────────────────────────────────────────────

    def get_product_by_id(self, tenant_id: uuid.UUID, product_id: uuid.UUID) -> Product:
        product = self.db.scalar(
            select(Product).where(
                Product.tenant_id == tenant_id,
                Product.id == product_id,
            )
        )
        if product is None:
            raise NotFoundError(f"Product {product_id} not found")
        return product

    def get_product_by_code(self, tenant_id: uuid.UUID, product_code: str) -> Product | None:
        return self.db.scalar(
            select(Product).where(
                Product.tenant_id == tenant_id,
                Product.product_code == product_code,
            )
        )

    def list_products(
        self,
        tenant_id: uuid.UUID,
        status: str = "active",
        skip: int = 0,
        limit: int = 50,
        search: str | None = None,
        category_id: uuid.UUID | None = None,
        brand_id: uuid.UUID | None = None,
    ) -> list[Product]:
        q = (
            select(Product)
            .where(Product.tenant_id == tenant_id, Product.status == status)
        )
        if search:
            pattern = f"%{search}%"
            q = q.where(
                Product.product_code.ilike(pattern) | Product.name.ilike(pattern)
            )
        if category_id is not None:
            q = q.where(Product.category_id == category_id)
        if brand_id is not None:
            q = q.where(Product.brand_id == brand_id)
        return list(
            self.db.scalars(q.order_by(Product.name).offset(skip).limit(limit))
        )

    def count_products_by_tenant(self, tenant_id: uuid.UUID) -> int:
        """Return the total product count for a tenant (used as sequence for code gen)."""
        result = self.db.scalar(
            select(func.count()).where(Product.tenant_id == tenant_id)
        )
        return result or 0

    # ── product writes ────────────────────────────────────────────────────────

    def create_product(
        self,
        tenant_id: uuid.UUID,
        product_code: str,
        name: str,
        category_id: uuid.UUID | None = None,
        product_group_id: uuid.UUID | None = None,
        product_type_id: uuid.UUID | None = None,
        brand_id: uuid.UUID | None = None,
        description: str | None = None,
        image_url: str | None = None,
    ) -> Product:
        if self.get_product_by_code(tenant_id, product_code) is not None:
            raise ConflictError(f"Product with code '{product_code}' already exists")
        product = Product(
            tenant_id=tenant_id,
            product_code=product_code,
            name=name,
            category_id=category_id,
            product_group_id=product_group_id,
            product_type_id=product_type_id,
            brand_id=brand_id,
            description=description,
            image_url=image_url,
            status="active",
        )
        self.db.add(product)
        self.db.flush()
        return product

    def update_product_image_url(
        self,
        tenant_id: uuid.UUID,
        product_id: uuid.UUID,
        image_url: str,
    ) -> Product:
        product = self.get_product_by_id(tenant_id, product_id)
        product.image_url = image_url
        self.db.flush()
        return product

    def soft_delete_product(self, tenant_id: uuid.UUID, product_id: uuid.UUID) -> Product:
        product = self.get_product_by_id(tenant_id, product_id)
        product.status = "deleted"
        self.db.flush()
        return product

    # ── variant reads ─────────────────────────────────────────────────────────

    def get_variant_by_id(self, tenant_id: uuid.UUID, variant_id: uuid.UUID) -> ProductVariant:
        variant = self.db.scalar(
            select(ProductVariant).where(
                ProductVariant.tenant_id == tenant_id,
                ProductVariant.id == variant_id,
            )
        )
        if variant is None:
            raise NotFoundError(f"ProductVariant {variant_id} not found")
        return variant

    def get_variant_by_sku(self, tenant_id: uuid.UUID, sku_code: str) -> ProductVariant | None:
        return self.db.scalar(
            select(ProductVariant).where(
                ProductVariant.tenant_id == tenant_id,
                ProductVariant.sku_code == sku_code,
            )
        )

    def list_variants_by_product(
        self, tenant_id: uuid.UUID, product_id: uuid.UUID
    ) -> list[ProductVariant]:
        return list(
            self.db.scalars(
                select(ProductVariant).where(
                    ProductVariant.tenant_id == tenant_id,
                    ProductVariant.product_id == product_id,
                    ProductVariant.status == "active",
                )
            )
        )

    # ── variant writes ────────────────────────────────────────────────────────

    def create_variant(
        self,
        tenant_id: uuid.UUID,
        product_id: uuid.UUID,
        size_id: uuid.UUID,
        color_id: uuid.UUID,
        sku_code: str,
        mrp: Decimal,
        selling_price: Decimal,
        cost_price: Decimal,
        fabric: str | None = None,
        reorder_level: int = 0,
    ) -> ProductVariant:
        if self.get_variant_by_sku(tenant_id, sku_code) is not None:
            raise ConflictError(f"ProductVariant with SKU '{sku_code}' already exists")
        variant = ProductVariant(
            tenant_id=tenant_id,
            product_id=product_id,
            size_id=size_id,
            color_id=color_id,
            sku_code=sku_code,
            mrp=mrp,
            selling_price=selling_price,
            cost_price=cost_price,
            fabric=fabric,
            reorder_level=reorder_level,
            status="active",
        )
        self.db.add(variant)
        self.db.flush()
        return variant

    def soft_delete_variant(
        self, tenant_id: uuid.UUID, variant_id: uuid.UUID
    ) -> ProductVariant:
        variant = self.get_variant_by_id(tenant_id, variant_id)
        variant.status = "deleted"
        self.db.flush()
        return variant
