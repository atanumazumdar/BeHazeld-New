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
import csv
import io
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.base import Base
from app.models.catalog import (
    Brand,
    Barcode,
    Category,
    Color,
    Product,
    ProductGroup,
    ProductType,
    ProductVariant,
    Size,
)
from app.models.tenant import Tenant  # noqa: F401 - registers tenant FK targets
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
    MasterDataImportResponse,
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

    def import_master_data_csv(
        self,
        tenant_id: uuid.UUID,
        entity_type: str,
        content: bytes,
    ) -> MasterDataImportResponse:
        entity_type = entity_type.strip().lower()
        self._ensure_master_tables_available()
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = content.decode("latin-1")
        text = self._normalize_csv_text(text)
        dialect = self._detect_csv_dialect(text)
        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
        if reader.fieldnames is None:
            raise ValueError("CSV file is empty or missing a header row")

        headers = {h.strip().lower() for h in reader.fieldnames if h}
        required = self._required_import_columns(entity_type)
        missing = sorted(required - headers)
        if missing:
            raise ValueError(f"Missing required CSV columns: {', '.join(missing)}")

        created = 0
        skipped = 0
        errors: list[str] = []
        existing_names = self._existing_master_names(tenant_id, entity_type)

        for line_number, raw_row in enumerate(reader, start=2):
            row = {
                (key or "").strip().lower(): (value or "").strip()
                for key, value in raw_row.items()
            }
            name = row.get("name", "")
            if not name:
                errors.append(f"Line {line_number}: name is required")
                continue

            name_key = name.casefold()
            if name_key in existing_names:
                skipped += 1
                continue

            try:
                self._create_master_from_import_row(tenant_id, entity_type, row)
                existing_names.add(name_key)
                created += 1
            except Exception as exc:  # noqa: BLE001
                errors.append(f"Line {line_number}: {exc}")

        self.db.commit()
        return MasterDataImportResponse(
            entity_type=entity_type,
            created=created,
            skipped=skipped,
            errors=errors,
        )

    def _ensure_master_tables_available(self) -> None:
        """Create catalog master tables on first-run production databases."""
        bind = self.db.get_bind()
        dialect_name = getattr(getattr(bind, "dialect", None), "name", None)
        if dialect_name != "postgresql":
            return

        with bind.begin() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS catalog"))

        Base.metadata.create_all(
            bind=bind,
            tables=[
                Category.__table__,
                ProductGroup.__table__,
                ProductType.__table__,
                Brand.__table__,
                Size.__table__,
                Color.__table__,
            ],
        )

    def _ensure_variant_image_column_available(self) -> None:
        """Add variant image storage on existing production catalog tables."""
        bind = self.db.get_bind()
        dialect_name = getattr(getattr(bind, "dialect", None), "name", None)
        if dialect_name != "postgresql":
            return

        with bind.begin() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS catalog"))
            conn.execute(
                text(
                    "ALTER TABLE IF EXISTS catalog.product_variants "
                    "ADD COLUMN IF NOT EXISTS image_url VARCHAR(500)"
                )
            )

    def _ensure_catalog_product_tables_available(self) -> None:
        """Create product/SKU catalog tables on first-run production databases."""
        self._ensure_master_tables_available()

        bind = self.db.get_bind()
        dialect_name = getattr(getattr(bind, "dialect", None), "name", None)
        if dialect_name != "postgresql":
            return

        Base.metadata.create_all(
            bind=bind,
            tables=[
                Product.__table__,
                ProductVariant.__table__,
                Barcode.__table__,
            ],
        )
        self._ensure_variant_image_column_available()

    def _required_import_columns(self, entity_type: str) -> set[str]:
        required_columns = {
            "categories": {"name"},
            "product-groups": {"name"},
            "product-types": {"name"},
            "brands": {"name"},
            "sizes": {"name"},
            "colors": {"name"},
        }
        if entity_type not in required_columns:
            raise ValueError(f"Unsupported master data type '{entity_type}'")
        return required_columns[entity_type]

    def _normalize_csv_text(self, text: str) -> str:
        """
        Handle spreadsheet exports that wrap a whole comma-separated row in quotes.
        Example: "name,description" should become name,description.
        """
        normalized_lines: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith('"') and stripped.endswith('"') and stripped.count('"') == 2:
                normalized_lines.append(stripped[1:-1])
            else:
                normalized_lines.append(line)
        return "\n".join(normalized_lines)

    def _detect_csv_dialect(self, text: str) -> csv.Dialect:
        sample = text[:4096]
        try:
            return csv.Sniffer().sniff(sample, delimiters=",\t;")
        except csv.Error:
            return csv.excel

    def _existing_master_names(self, tenant_id: uuid.UUID, entity_type: str) -> set[str]:
        models = {
            "categories": Category,
            "product-groups": ProductGroup,
            "product-types": ProductType,
            "brands": Brand,
            "sizes": Size,
            "colors": Color,
        }
        model = models[entity_type]
        return {
            name.casefold()
            for name in self.db.scalars(
                select(model.name).where(model.tenant_id == tenant_id)
            )
        }

    def _create_master_from_import_row(
        self,
        tenant_id: uuid.UUID,
        entity_type: str,
        row: dict[str, str],
    ) -> None:
        name = row["name"]
        if entity_type == "categories":
            self.repo.create_category(
                tenant_id=tenant_id,
                name=name,
                description=row.get("description") or None,
                sort_order=self._parse_non_negative_int(row.get("sort_order"), "sort_order"),
            )
        elif entity_type == "product-groups":
            self.repo.create_product_group(
                tenant_id=tenant_id,
                name=name,
                description=row.get("description") or None,
            )
        elif entity_type == "product-types":
            self.repo.create_product_type(tenant_id=tenant_id, name=name)
        elif entity_type == "brands":
            self.repo.create_brand(tenant_id=tenant_id, name=name)
        elif entity_type == "sizes":
            self.repo.create_size(
                tenant_id=tenant_id,
                name=name,
                sort_order=self._parse_non_negative_int(row.get("sort_order"), "sort_order"),
            )
        elif entity_type == "colors":
            CreateColorRequest(name=name, hex_code=row.get("hex_code") or None)
            self.repo.create_color(
                tenant_id=tenant_id,
                name=name,
                hex_code=row.get("hex_code") or None,
            )

    def _parse_non_negative_int(self, value: str | None, field_name: str) -> int:
        if value in (None, ""):
            return 0
        try:
            parsed = int(value)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be a whole number") from exc
        if parsed < 0:
            raise ValueError(f"{field_name} must be greater than or equal to 0")
        return parsed

    # ── product writes ────────────────────────────────────────────────────────

    def create_product(
        self, tenant_id: uuid.UUID, req: CreateProductRequest
    ) -> Product:
        """
        Auto-generate product_code from the first letters of the product name.
        """
        self._ensure_catalog_product_tables_available()
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
        self._ensure_catalog_product_tables_available()
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
            image_url=req.image_url,
            reorder_level=req.reorder_level,
        )
        self.db.commit()
        self.db.refresh(variant)
        return variant

    def upload_variant_image(
        self,
        tenant_id: uuid.UUID,
        product_id: uuid.UUID,
        variant_id: uuid.UUID,
        file,
        filename: str | None = None,
    ) -> ProductVariant:
        self._ensure_catalog_product_tables_available()
        product = self.repo.get_product_by_id(tenant_id, product_id)
        variant = self.repo.get_variant_by_id(tenant_id, variant_id)
        if variant.product_id != product.id:
            raise NotFoundError(f"ProductVariant {variant_id} not found for product {product_id}")

        image_url = ImageService().upload_variant_image(
            file,
            tenant_id=tenant_id,
            product_id=product_id,
            variant_id=variant_id,
            filename=filename,
        )
        variant = self.repo.update_variant_image_url(tenant_id, variant_id, image_url)
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
        self._ensure_catalog_product_tables_available()
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
        self._ensure_catalog_product_tables_available()
        return self.repo.get_product_by_id(tenant_id, product_id)

    def upload_product_image(
        self,
        tenant_id: uuid.UUID,
        product_id: uuid.UUID,
        file,
        *,
        filename: str | None = None,
    ) -> Product:
        self._ensure_catalog_product_tables_available()
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
        self._ensure_catalog_product_tables_available()
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
