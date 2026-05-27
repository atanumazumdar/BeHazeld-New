"""Catalog model structure tests — no live DB required."""
import uuid
from decimal import Decimal

import pytest


def test_category_has_required_fields() -> None:
    from app.models.catalog import Category
    tenant_id = uuid.uuid4()
    cat = Category(
        tenant_id=tenant_id,
        name="Men's Wear",
        sort_order=1,
    )
    assert cat.name == "Men's Wear"
    assert cat.sort_order == 1
    assert cat.tenant_id == tenant_id


def test_product_group_has_required_fields() -> None:
    from app.models.catalog import ProductGroup
    pg = ProductGroup(tenant_id=uuid.uuid4(), name="Summer 2026")
    assert pg.name == "Summer 2026"


def test_brand_has_required_fields() -> None:
    from app.models.catalog import Brand
    b = Brand(tenant_id=uuid.uuid4(), name="BeHazel'd")
    assert b.name == "BeHazel'd"


def test_size_has_sort_order() -> None:
    from app.models.catalog import Size
    s = Size(tenant_id=uuid.uuid4(), name="XL", sort_order=5)
    assert s.sort_order == 5


def test_color_has_hex_code() -> None:
    from app.models.catalog import Color
    c = Color(tenant_id=uuid.uuid4(), name="Midnight Blue", hex_code="#003153")
    assert c.hex_code == "#003153"


def test_product_fields_and_status() -> None:
    from app.models.catalog import Product
    p = Product(
        tenant_id=uuid.uuid4(),
        product_code="SUM-KURT-0001",
        name="Summer Kurti",
        status="active",
    )
    assert p.product_code == "SUM-KURT-0001"
    assert p.status == "active"
    # server_default ensures DB uses "active" when status is omitted at INSERT
    col = Product.__table__.c["status"]
    assert col.server_default is not None


def test_product_variant_pricing() -> None:
    from app.models.catalog import ProductVariant
    v = ProductVariant(
        tenant_id=uuid.uuid4(),
        product_id=uuid.uuid4(),
        size_id=uuid.uuid4(),
        color_id=uuid.uuid4(),
        sku_code="SUM-KURT-0001-XLMBL",
        mrp=Decimal("1299.00"),
        selling_price=Decimal("999.00"),
        cost_price=Decimal("450.00"),
        status="active",
    )
    assert v.mrp == Decimal("1299.00")
    assert v.selling_price == Decimal("999.00")
    assert v.cost_price == Decimal("450.00")
    assert v.status == "active"


def test_barcode_has_type() -> None:
    from app.models.catalog import Barcode
    b = Barcode(
        tenant_id=uuid.uuid4(),
        variant_id=uuid.uuid4(),
        value="8901030837943",
        barcode_type="EAN13",
    )
    assert b.barcode_type == "EAN13"


def test_generate_product_code_format() -> None:
    from app.repositories.catalog_repository import generate_product_code
    code = generate_product_code("Summer Collection", "Kurti", 1)
    assert code == "SUM-KURT-0001"


def test_generate_product_code_pads_sequence() -> None:
    from app.repositories.catalog_repository import generate_product_code
    code = generate_product_code("Winter", "Jacket", 42)
    assert code == "WIN-JACK-0042"


def test_generate_product_code_handles_short_names() -> None:
    from app.repositories.catalog_repository import generate_product_code
    code = generate_product_code("Go", "T", 1)
    assert code == "GO-T-0001"


def test_generate_sku_code_format() -> None:
    from app.repositories.catalog_repository import generate_sku_code
    sku = generate_sku_code("SUM-KURT-0001", "XL", "Midnight Blue")
    assert sku == "SUM-KURT-0001-XLMID"


def test_generate_sku_code_short_size_color() -> None:
    from app.repositories.catalog_repository import generate_sku_code
    sku = generate_sku_code("WIN-JACK-0042", "S", "Red")
    assert sku == "WIN-JACK-0042-SRED"
