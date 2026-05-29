"""
Catalog repository — pure data access layer for the catalog schema.

Rule: every read method receives tenant_id as its first argument and uses it
as the primary WHERE filter. This is the only place in the codebase where raw
SQLAlchemy queries for catalog data are written.

Module-level helpers
--------------------
generate_product_code(group_name, product_name, seq) → str
    Pure function — deterministic, no DB calls. Called by the service layer,
    keeping the legacy signature while generating initials from product name.

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

    Format: first letters of each product name word.
    Examples:
      ("Power Edit Georgette Kurti") → "PEGK"
      ("Peach Kurta")                → "PK"
    """
    del group_name, seq
    words = [word for word in product_name.strip().replace("-", " ").split() if word]
    initials = "".join(word[0].upper() for word in words)
    return initials or product_name.strip().upper().replace(" ", "")[:4]


def generate_sku_code(product_code: str, size_name: str, color_name: str) -> str:
    """
    Append color + size suffixes to the product code to form the SKU.

    Format: {product_code}-{COLOR_CODE}-{SIZE}
    Examples:
      ("PEGK", "42", "Peach")         → "PEGK-PCH-42"
      ("PK",   "M",  "Red")           → "PK-RED-M"
    """
    s = size_name.strip().upper().replace(" ", "")
    raw_color = "".join(ch for ch in color_name.strip().upper() if ch.isalnum())
    color_without_vowels = raw_color[:1] + "".join(
        ch for ch in raw_color[1:] if ch not in {"A", "E", "I", "O", "U"}
    )
    c = (color_without_vowels if len(color_without_vowels) >= 3 else raw_color)[:3]
    return f"{product_code}-{c}-{s}"


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

    def update_category(
        self,
        tenant_id: uuid.UUID,
        category_id: uuid.UUID,
        name: str,
        description: str | None = None,
        sort_order: int = 0,
    ) -> Category:
        obj = self.db.scalar(select(Category).where(Category.tenant_id == tenant_id, Category.id == category_id))
        if obj is None:
            raise NotFoundError(f"Category {category_id} not found")
        obj.name = name
        obj.description = description
        obj.sort_order = sort_order
        self.db.flush()
        return obj

    def update_product_group(
        self,
        tenant_id: uuid.UUID,
        group_id: uuid.UUID,
        name: str,
        description: str | None = None,
    ) -> ProductGroup:
        obj = self.get_product_group_by_id(tenant_id, group_id)
        if obj is None:
            raise NotFoundError(f"ProductGroup {group_id} not found")
        obj.name = name
        obj.description = description
        self.db.flush()
        return obj

    def update_product_type(
        self, tenant_id: uuid.UUID, type_id: uuid.UUID, name: str
    ) -> ProductType:
        obj = self.db.scalar(select(ProductType).where(ProductType.tenant_id == tenant_id, ProductType.id == type_id))
        if obj is None:
            raise NotFoundError(f"ProductType {type_id} not found")
        obj.name = name
        self.db.flush()
        return obj

    def update_brand(self, tenant_id: uuid.UUID, brand_id: uuid.UUID, name: str) -> Brand:
        obj = self.db.scalar(select(Brand).where(Brand.tenant_id == tenant_id, Brand.id == brand_id))
        if obj is None:
            raise NotFoundError(f"Brand {brand_id} not found")
        obj.name = name
        self.db.flush()
        return obj

    def update_size(
        self, tenant_id: uuid.UUID, size_id: uuid.UUID, name: str, sort_order: int = 0
    ) -> Size:
        obj = self.get_size_by_id(tenant_id, size_id)
        if obj is None:
            raise NotFoundError(f"Size {size_id} not found")
        obj.name = name
        obj.sort_order = sort_order
        self.db.flush()
        return obj

    def update_color(
        self, tenant_id: uuid.UUID, color_id: uuid.UUID, name: str, hex_code: str | None = None
    ) -> Color:
        obj = self.get_color_by_id(tenant_id, color_id)
        if obj is None:
            raise NotFoundError(f"Color {color_id} not found")
        obj.name = name
        obj.hex_code = hex_code
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

    def update_product(
        self,
        tenant_id: uuid.UUID,
        product_id: uuid.UUID,
        product_code: str,
        name: str,
        category_id: uuid.UUID | None = None,
        product_group_id: uuid.UUID | None = None,
        product_type_id: uuid.UUID | None = None,
        brand_id: uuid.UUID | None = None,
        description: str | None = None,
        image_url: str | None = None,
    ) -> Product:
        product = self.get_product_by_id(tenant_id, product_id)
        existing = self.get_product_by_code(tenant_id, product_code)
        if existing is not None and existing.id != product.id:
            raise ConflictError(f"Product with code '{product_code}' already exists")

        product.product_code = product_code
        product.name = name
        product.category_id = category_id
        product.product_group_id = product_group_id
        product.product_type_id = product_type_id
        product.brand_id = brand_id
        product.description = description
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
        image_url: str | None = None,
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
            image_url=image_url,
            reorder_level=reorder_level,
            status="active",
        )
        self.db.add(variant)
        self.db.flush()
        return variant

    def update_variant_image_url(
        self,
        tenant_id: uuid.UUID,
        variant_id: uuid.UUID,
        image_url: str,
    ) -> ProductVariant:
        variant = self.get_variant_by_id(tenant_id, variant_id)
        variant.image_url = image_url
        self.db.flush()
        return variant

    def update_variant(
        self,
        tenant_id: uuid.UUID,
        variant_id: uuid.UUID,
        size_id: uuid.UUID,
        color_id: uuid.UUID,
        sku_code: str,
        mrp: Decimal,
        selling_price: Decimal,
        cost_price: Decimal,
        fabric: str | None = None,
        image_url: str | None = None,
        reorder_level: int = 0,
    ) -> ProductVariant:
        variant = self.get_variant_by_id(tenant_id, variant_id)
        existing = self.get_variant_by_sku(tenant_id, sku_code)
        if existing is not None and existing.id != variant.id:
            raise ConflictError(f"ProductVariant with SKU '{sku_code}' already exists")

        variant.size_id = size_id
        variant.color_id = color_id
        variant.sku_code = sku_code
        variant.mrp = mrp
        variant.selling_price = selling_price
        variant.cost_price = cost_price
        variant.fabric = fabric
        if image_url is not None:
            variant.image_url = image_url
        variant.reorder_level = reorder_level
        self.db.flush()
        return variant

    def soft_delete_variant(
        self, tenant_id: uuid.UUID, variant_id: uuid.UUID
    ) -> ProductVariant:
        variant = self.get_variant_by_id(tenant_id, variant_id)
        variant.status = "deleted"
        self.db.flush()
        return variant
