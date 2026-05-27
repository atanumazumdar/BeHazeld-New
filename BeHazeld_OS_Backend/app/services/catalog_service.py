"""
CatalogService — business logic for catalog domain.

Responsibilities
----------------
- Auto-generate product_code using group name + global sequence
- Validate FK references (size, color, product_group) before writing
- Delegate all raw DB access to CatalogRepository
- Commit or rollback the session; callers must not manage transactions
"""
import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.catalog import (
    Brand,
    Category,
    Color,
    Product,
    ProductGroup,
    ProductType,
    ProductVariant,
    Size,
)
from app.repositories.catalog_repository import (
    CatalogRepository,
    generate_product_code,
    generate_sku_code,
)
from app.schemas.catalog import (
    CreateBrandRequest,
    CreateCategoryRequest,
    CreateColorRequest,
    CreateProductGroupRequest,
    CreateProductRequest,
    CreateProductTypeRequest,
    CreateSizeRequest,
    CreateVariantRequest,
)
from app.services.image_service import ImageService


class CatalogService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = CatalogRepository(db)

    # ── master writes ─────────────────────────────────────────────────────────

    def create_category(
        self, tenant_id: uuid.UUID, req: CreateCategoryRequest
    ) -> Category:
        obj = self.repo.create_category(
            tenant_id=tenant_id,
            name=req.name,
            description=req.description,
            sort_order=req.sort_order,
        )
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def create_product_group(
        self, tenant_id: uuid.UUID, req: CreateProductGroupRequest
    ) -> ProductGroup:
        obj = self.repo.create_product_group(
            tenant_id=tenant_id,
            name=req.name,
            description=req.description,
        )
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def create_product_type(
        self, tenant_id: uuid.UUID, req: CreateProductTypeRequest
    ) -> ProductType:
        obj = self.repo.create_product_type(tenant_id=tenant_id, name=req.name)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def create_brand(
        self, tenant_id: uuid.UUID, req: CreateBrandRequest
    ) -> Brand:
        obj = self.repo.create_brand(tenant_id=tenant_id, name=req.name)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def create_size(
        self, tenant_id: uuid.UUID, req: CreateSizeRequest
    ) -> Size:
        obj = self.repo.create_size(
            tenant_id=tenant_id, name=req.name, sort_order=req.sort_order
        )
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def create_color(
        self, tenant_id: uuid.UUID, req: CreateColorRequest
    ) -> Color:
        obj = self.repo.create_color(
            tenant_id=tenant_id, name=req.name, hex_code=req.hex_code
        )
        self.db.commit()
        self.db.refresh(obj)
        return obj

    # ── product writes ────────────────────────────────────────────────────────

    def create_product(
        self, tenant_id: uuid.UUID, req: CreateProductRequest
    ) -> Product:
        """
        Auto-generate product_code from group name (or product name) + sequence.

        Sequence = count_products_by_tenant() + 1  (1-based, ever-increasing).
        When no product_group_id is supplied the product name is used for both
        the group and name prefix slots of generate_product_code().
        """
        seq = self.repo.count_products_by_tenant(tenant_id) + 1

        if req.product_group_id is not None:
            group = self.repo.get_product_group_by_id(tenant_id, req.product_group_id)
            if group is None:
                raise NotFoundError(
                    f"ProductGroup {req.product_group_id} not found for this tenant"
                )
            group_name = group.name
        else:
            group_name = req.name  # fallback: use product name as group prefix

        product_code = generate_product_code(group_name, req.name, seq)

        product = self.repo.create_product(
            tenant_id=tenant_id,
            product_code=product_code,
            name=req.name,
            category_id=req.category_id,
            product_group_id=req.product_group_id,
            product_type_id=req.product_type_id,
            brand_id=req.brand_id,
            description=req.description,
            image_url=req.image_url,
        )
        self.db.commit()
        self.db.refresh(product)
        return product

    # ── variant writes ────────────────────────────────────────────────────────

    def create_variant(
        self,
        tenant_id: uuid.UUID,
        product_id: uuid.UUID,
        req: CreateVariantRequest,
    ) -> ProductVariant:
        """
        Validate size + color existence, then generate the SKU and create the variant.
        """
        # Validate parent product exists
        product = self.repo.get_product_by_id(tenant_id, product_id)  # raises NotFoundError

        size = self.repo.get_size_by_id(tenant_id, req.size_id)
        if size is None:
            raise NotFoundError(f"Size {req.size_id} not found for this tenant")

        color = self.repo.get_color_by_id(tenant_id, req.color_id)
        if color is None:
            raise NotFoundError(f"Color {req.color_id} not found for this tenant")

        sku_code = generate_sku_code(product.product_code, size.name, color.name)

        variant = self.repo.create_variant(
            tenant_id=tenant_id,
            product_id=product_id,
            size_id=req.size_id,
            color_id=req.color_id,
            sku_code=sku_code,
            mrp=req.mrp,
            selling_price=req.selling_price,
            cost_price=req.cost_price,
            fabric=req.fabric,
            reorder_level=req.reorder_level,
        )
        self.db.commit()
        self.db.refresh(variant)
        return variant

    # ── reads (pass-through to repo) ─────────────────────────────────────────

    def list_categories(self, tenant_id: uuid.UUID) -> list[Category]:
        return self.repo.list_categories(tenant_id)

    def list_product_groups(self, tenant_id: uuid.UUID) -> list[ProductGroup]:
        return self.repo.list_product_groups(tenant_id)

    def list_product_types(self, tenant_id: uuid.UUID) -> list[ProductType]:
        return self.repo.list_product_types(tenant_id)

    def list_brands(self, tenant_id: uuid.UUID) -> list[Brand]:
        return self.repo.list_brands(tenant_id)

    def list_sizes(self, tenant_id: uuid.UUID) -> list[Size]:
        return self.repo.list_sizes(tenant_id)

    def list_colors(self, tenant_id: uuid.UUID) -> list[Color]:
        return self.repo.list_colors(tenant_id)

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
        return self.repo.list_products(
            tenant_id,
            status=status,
            skip=skip,
            limit=limit,
            search=search,
            category_id=category_id,
            brand_id=brand_id,
        )

    def get_product(self, tenant_id: uuid.UUID, product_id: uuid.UUID) -> Product:
        return self.repo.get_product_by_id(tenant_id, product_id)

    def upload_product_image(
        self,
        tenant_id: uuid.UUID,
        product_id: uuid.UUID,
        file,
        *,
        filename: str | None = None,
    ) -> Product:
        self.repo.get_product_by_id(tenant_id, product_id)
        image_url = ImageService().upload_product_image(
            file,
            tenant_id=tenant_id,
            product_id=product_id,
            filename=filename,
        )
        product = self.repo.update_product_image_url(tenant_id, product_id, image_url)
        self.db.commit()
        self.db.refresh(product)
        return product

    def list_variants(self, tenant_id: uuid.UUID, product_id: uuid.UUID) -> list[ProductVariant]:
        return self.repo.list_variants_by_product(tenant_id, product_id)

    def soft_delete_product(self, tenant_id: uuid.UUID, product_id: uuid.UUID) -> Product:
        product = self.repo.soft_delete_product(tenant_id, product_id)
        self.db.commit()
        self.db.refresh(product)
        return product

    def soft_delete_variant(
        self, tenant_id: uuid.UUID, variant_id: uuid.UUID
    ) -> ProductVariant:
        variant = self.repo.soft_delete_variant(tenant_id, variant_id)
        self.db.commit()
        self.db.refresh(variant)
        return variant
