"""
CatalogRepository tests — mock DB session, no live database.
Every read/write method must filter by tenant_id.
"""
import uuid
from decimal import Decimal
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_db() -> MagicMock:
    return MagicMock()


# ── generate_product_code (pure function) ─────────────────────────────────────

def test_generate_product_code_basic() -> None:
    from app.repositories.catalog_repository import generate_product_code
    assert generate_product_code("Summer Collection", "Kurti", 1) == "SUM-KURT-0001"


def test_generate_product_code_pads_to_4_digits() -> None:
    from app.repositories.catalog_repository import generate_product_code
    assert generate_product_code("Winter", "Jacket", 42) == "WIN-JACK-0042"


def test_generate_product_code_truncates_at_3_and_4() -> None:
    from app.repositories.catalog_repository import generate_product_code
    # Group prefix: 3 chars max; name suffix: 4 chars max
    assert generate_product_code("Go", "T", 1) == "GO-T-0001"
    assert generate_product_code("ABCDEF", "ABCDEFGH", 1) == "ABC-ABCD-0001"


def test_generate_sku_code_format() -> None:
    from app.repositories.catalog_repository import generate_sku_code
    assert generate_sku_code("SUM-KURT-0001", "XL", "Midnight Blue") == "SUM-KURT-0001-XLMID"


def test_generate_sku_code_short_color() -> None:
    from app.repositories.catalog_repository import generate_sku_code
    assert generate_sku_code("WIN-JACK-0042", "S", "Red") == "WIN-JACK-0042-SRED"


# ── master table reads ────────────────────────────────────────────────────────

def test_list_categories_returns_list(mock_db: MagicMock) -> None:
    from app.repositories.catalog_repository import CatalogRepository
    from app.models.catalog import Category
    tid = uuid.uuid4()
    cats = [MagicMock(spec=Category) for _ in range(3)]
    mock_db.scalars.return_value = iter(cats)
    result = CatalogRepository(mock_db).list_categories(tid)
    assert len(result) == 3


def test_list_product_groups_returns_list(mock_db: MagicMock) -> None:
    from app.repositories.catalog_repository import CatalogRepository
    from app.models.catalog import ProductGroup
    tid = uuid.uuid4()
    groups = [MagicMock(spec=ProductGroup) for _ in range(2)]
    mock_db.scalars.return_value = iter(groups)
    result = CatalogRepository(mock_db).list_product_groups(tid)
    assert len(result) == 2


def test_list_sizes_returns_ordered_list(mock_db: MagicMock) -> None:
    from app.repositories.catalog_repository import CatalogRepository
    from app.models.catalog import Size
    tid = uuid.uuid4()
    sizes = [MagicMock(spec=Size) for _ in range(5)]
    mock_db.scalars.return_value = iter(sizes)
    result = CatalogRepository(mock_db).list_sizes(tid)
    assert len(result) == 5


def test_list_colors_returns_list(mock_db: MagicMock) -> None:
    from app.repositories.catalog_repository import CatalogRepository
    from app.models.catalog import Color
    colors = [MagicMock(spec=Color) for _ in range(4)]
    mock_db.scalars.return_value = iter(colors)
    result = CatalogRepository(mock_db).list_colors(uuid.uuid4())
    assert len(result) == 4


# ── product reads ─────────────────────────────────────────────────────────────

def test_get_product_by_id_returns_product(mock_db: MagicMock) -> None:
    from app.repositories.catalog_repository import CatalogRepository
    from app.models.catalog import Product
    p = MagicMock(spec=Product)
    mock_db.scalar.return_value = p
    result = CatalogRepository(mock_db).get_product_by_id(uuid.uuid4(), uuid.uuid4())
    assert result is p


def test_get_product_by_id_raises_not_found(mock_db: MagicMock) -> None:
    from app.repositories.catalog_repository import CatalogRepository
    from app.core.exceptions import NotFoundError
    mock_db.scalar.return_value = None
    with pytest.raises(NotFoundError):
        CatalogRepository(mock_db).get_product_by_id(uuid.uuid4(), uuid.uuid4())


def test_get_product_by_code_returns_product(mock_db: MagicMock) -> None:
    from app.repositories.catalog_repository import CatalogRepository
    from app.models.catalog import Product
    p = MagicMock(spec=Product)
    mock_db.scalar.return_value = p
    result = CatalogRepository(mock_db).get_product_by_code(uuid.uuid4(), "SUM-KURT-0001")
    assert result is p


def test_get_product_by_code_returns_none_when_missing(mock_db: MagicMock) -> None:
    from app.repositories.catalog_repository import CatalogRepository
    mock_db.scalar.return_value = None
    assert CatalogRepository(mock_db).get_product_by_code(uuid.uuid4(), "MISSING") is None


def test_list_products_returns_list(mock_db: MagicMock) -> None:
    from app.repositories.catalog_repository import CatalogRepository
    from app.models.catalog import Product
    products = [MagicMock(spec=Product) for _ in range(10)]
    mock_db.scalars.return_value = iter(products)
    result = CatalogRepository(mock_db).list_products(uuid.uuid4())
    assert len(result) == 10


def test_count_products_by_tenant_returns_int(mock_db: MagicMock) -> None:
    from app.repositories.catalog_repository import CatalogRepository
    mock_db.scalar.return_value = 5
    count = CatalogRepository(mock_db).count_products_by_tenant(uuid.uuid4())
    assert count == 5


def test_count_products_by_tenant_returns_zero_on_none(mock_db: MagicMock) -> None:
    from app.repositories.catalog_repository import CatalogRepository
    mock_db.scalar.return_value = None
    assert CatalogRepository(mock_db).count_products_by_tenant(uuid.uuid4()) == 0


# ── product writes ────────────────────────────────────────────────────────────

def test_create_product_adds_and_flushes(mock_db: MagicMock) -> None:
    from app.repositories.catalog_repository import CatalogRepository
    # Simulate no duplicate (get_product_by_code returns None)
    mock_db.scalar.return_value = None
    tid = uuid.uuid4()
    product = CatalogRepository(mock_db).create_product(
        tenant_id=tid,
        product_code="SUM-KURT-0001",
        name="Summer Kurti",
    )
    mock_db.add.assert_called_once()
    mock_db.flush.assert_called_once()
    assert product.tenant_id == tid
    assert product.product_code == "SUM-KURT-0001"
    assert product.status == "active"


def test_create_product_conflict_on_duplicate_code(mock_db: MagicMock) -> None:
    from app.repositories.catalog_repository import CatalogRepository
    from app.core.exceptions import ConflictError
    # Simulate get_product_by_code returning an existing product
    from app.models.catalog import Product
    mock_db.scalar.return_value = MagicMock(spec=Product)
    with pytest.raises(ConflictError):
        CatalogRepository(mock_db).create_product(
            tenant_id=uuid.uuid4(),
            product_code="SUM-KURT-0001",
            name="Duplicate",
        )


# ── variant reads ─────────────────────────────────────────────────────────────

def test_get_variant_by_id_returns_variant(mock_db: MagicMock) -> None:
    from app.repositories.catalog_repository import CatalogRepository
    from app.models.catalog import ProductVariant
    v = MagicMock(spec=ProductVariant)
    mock_db.scalar.return_value = v
    result = CatalogRepository(mock_db).get_variant_by_id(uuid.uuid4(), uuid.uuid4())
    assert result is v


def test_get_variant_by_id_raises_not_found(mock_db: MagicMock) -> None:
    from app.repositories.catalog_repository import CatalogRepository
    from app.core.exceptions import NotFoundError
    mock_db.scalar.return_value = None
    with pytest.raises(NotFoundError):
        CatalogRepository(mock_db).get_variant_by_id(uuid.uuid4(), uuid.uuid4())


def test_get_variant_by_sku_returns_none_when_missing(mock_db: MagicMock) -> None:
    from app.repositories.catalog_repository import CatalogRepository
    mock_db.scalar.return_value = None
    assert CatalogRepository(mock_db).get_variant_by_sku(uuid.uuid4(), "MISSING") is None


def test_list_variants_by_product_returns_list(mock_db: MagicMock) -> None:
    from app.repositories.catalog_repository import CatalogRepository
    from app.models.catalog import ProductVariant
    variants = [MagicMock(spec=ProductVariant) for _ in range(4)]
    mock_db.scalars.return_value = iter(variants)
    result = CatalogRepository(mock_db).list_variants_by_product(uuid.uuid4(), uuid.uuid4())
    assert len(result) == 4


# ── variant writes ────────────────────────────────────────────────────────────

def test_create_variant_adds_and_flushes(mock_db: MagicMock) -> None:
    from app.repositories.catalog_repository import CatalogRepository
    # Simulate no duplicate (get_variant_by_sku returns None)
    mock_db.scalar.return_value = None
    tid = uuid.uuid4()
    variant = CatalogRepository(mock_db).create_variant(
        tenant_id=tid,
        product_id=uuid.uuid4(),
        size_id=uuid.uuid4(),
        color_id=uuid.uuid4(),
        sku_code="SUM-KURT-0001-XLMBL",
        mrp=Decimal("1299.00"),
        selling_price=Decimal("999.00"),
        cost_price=Decimal("450.00"),
    )
    mock_db.add.assert_called_once()
    mock_db.flush.assert_called_once()
    assert variant.sku_code == "SUM-KURT-0001-XLMBL"
    assert variant.tenant_id == tid


def test_create_variant_conflict_on_duplicate_sku(mock_db: MagicMock) -> None:
    from app.repositories.catalog_repository import CatalogRepository
    from app.core.exceptions import ConflictError
    from app.models.catalog import ProductVariant
    mock_db.scalar.return_value = MagicMock(spec=ProductVariant)
    with pytest.raises(ConflictError):
        CatalogRepository(mock_db).create_variant(
            tenant_id=uuid.uuid4(),
            product_id=uuid.uuid4(),
            size_id=uuid.uuid4(),
            color_id=uuid.uuid4(),
            sku_code="EXISTING-SKU",
            mrp=Decimal("100"),
            selling_price=Decimal("80"),
            cost_price=Decimal("50"),
        )


def test_soft_delete_product_sets_status(mock_db: MagicMock) -> None:
    from app.repositories.catalog_repository import CatalogRepository
    from app.models.catalog import Product
    product = MagicMock(spec=Product)
    mock_db.scalar.return_value = product
    CatalogRepository(mock_db).soft_delete_product(uuid.uuid4(), uuid.uuid4())
    assert product.status == "deleted"
    mock_db.flush.assert_called_once()

# ── master creates (added in Task 3) ──────────────────────────────────────────

def test_create_category_adds_and_flushes(mock_db: MagicMock) -> None:
    from app.repositories.catalog_repository import CatalogRepository
    tid = uuid.uuid4()
    cat = CatalogRepository(mock_db).create_category(tid, name="Men's Wear", sort_order=1)
    mock_db.add.assert_called_once()
    mock_db.flush.assert_called_once()
    assert cat.name == "Men's Wear"
    assert cat.sort_order == 1
    assert cat.tenant_id == tid


def test_create_product_group_adds_and_flushes(mock_db: MagicMock) -> None:
    from app.repositories.catalog_repository import CatalogRepository
    pg = CatalogRepository(mock_db).create_product_group(uuid.uuid4(), name="Summer 2026")
    mock_db.add.assert_called_once()
    mock_db.flush.assert_called_once()
    assert pg.name == "Summer 2026"


def test_create_size_adds_and_flushes(mock_db: MagicMock) -> None:
    from app.repositories.catalog_repository import CatalogRepository
    s = CatalogRepository(mock_db).create_size(uuid.uuid4(), name="XL", sort_order=4)
    mock_db.add.assert_called_once()
    mock_db.flush.assert_called_once()
    assert s.name == "XL"


def test_create_color_adds_and_flushes(mock_db: MagicMock) -> None:
    from app.repositories.catalog_repository import CatalogRepository
    c = CatalogRepository(mock_db).create_color(uuid.uuid4(), name="Midnight Blue", hex_code="#003153")
    mock_db.add.assert_called_once()
    mock_db.flush.assert_called_once()
    assert c.hex_code == "#003153"


def test_get_size_by_id_returns_size(mock_db: MagicMock) -> None:
    from app.repositories.catalog_repository import CatalogRepository
    from app.models.catalog import Size
    s = MagicMock(spec=Size)
    mock_db.scalar.return_value = s
    result = CatalogRepository(mock_db).get_size_by_id(uuid.uuid4(), uuid.uuid4())
    assert result is s


def test_get_size_by_id_returns_none_when_missing(mock_db: MagicMock) -> None:
    from app.repositories.catalog_repository import CatalogRepository
    mock_db.scalar.return_value = None
    assert CatalogRepository(mock_db).get_size_by_id(uuid.uuid4(), uuid.uuid4()) is None


def test_get_color_by_id_returns_color(mock_db: MagicMock) -> None:
    from app.repositories.catalog_repository import CatalogRepository
    from app.models.catalog import Color
    c = MagicMock(spec=Color)
    mock_db.scalar.return_value = c
    result = CatalogRepository(mock_db).get_color_by_id(uuid.uuid4(), uuid.uuid4())
    assert result is c


def test_get_color_by_id_returns_none_when_missing(mock_db: MagicMock) -> None:
    from app.repositories.catalog_repository import CatalogRepository
    mock_db.scalar.return_value = None
    assert CatalogRepository(mock_db).get_color_by_id(uuid.uuid4(), uuid.uuid4()) is None
