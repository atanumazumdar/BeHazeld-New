"""
Public Catalog API — no authentication required.

All endpoints are read-only for the catalog (no writes to product data).
Customer self-registration is the only write endpoint.

Route design
------------
Every route takes `tenant_id` as a path parameter so this API can serve
multiple tenants from the same deployment.  The storefront embeds the
tenant's UUID in its build config.

GET  /{tenant_id}/products                   — paginated active products
GET  /{tenant_id}/products/{product_id}      — single product + variants
GET  /{tenant_id}/categories                 — category list (flat)
GET  /{tenant_id}/product-groups             — product group / collection list
POST /{tenant_id}/checkout                   — storefront checkout / WhatsApp order
POST /{tenant_id}/customers/register         — customer self-registration

Performance notes
-----------------
* PublicRepository uses Core SELECT (no lazy loads).
* Variant list is loaded in a second targeted query (avoids N+1 on product list).
* No joinedload on the product list — only product-level data is returned in
  the list; full detail (with variants) is returned on GET /{product_id}.
"""
import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.core.pricing import gst_rate_for, price_with_gst
from app.db.session import get_db
from app.models.catalog import ProductVariant
from app.models.sales import Customer, SalePaymentMode
from app.repositories.public_repository import PublicRepository
from app.schemas.public import (
    PaginatedProductsResponse,
    PublicCategoryResponse,
    PublicCheckoutRequest,
    PublicCheckoutResponse,
    PublicCustomerResponse,
    PublicProductGroupResponse,
    PublicProductResponse,
    PublicRegisterCustomerRequest,
    PublicVariantResponse,
)
from app.schemas.sales import (
    CreateSaleBillLineRequest,
    CreateSaleBillRequest,
    CreateSalePaymentRequest,
)
from app.services.inventory_service import InventoryService
from app.services.sales_service import SalesService

router = APIRouter(prefix="/public", tags=["public"])


def _mark_uncached(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"


def _public_variant_response(v, stock_count) -> PublicVariantResponse:
    """Map an internal ProductVariant to the public storefront contract."""
    available = stock_count > 0
    return PublicVariantResponse(
        id=v.id,
        sku_code=v.sku_code,
        size_id=v.size_id,
        size_name=v.size.name,
        color_id=v.color_id,
        color_name=v.color.name,
        color_hex_code=v.color.hex_code,
        fabric=v.fabric,
        image_url=v.image_url,
        mrp=v.mrp,
        selling_price=price_with_gst(Decimal(str(v.selling_price)), date.today()),
        stock_count=stock_count,
        is_available=v.status == "active" and available,
        status=v.status,
    )


def _public_product_response(p, variants, stock_by_variant) -> PublicProductResponse:
    """Map an internal Product to the public storefront contract."""
    return PublicProductResponse(
        id=p.id,
        category_id=p.category_id,
        category_name=p.category.name if p.category else None,
        product_group_id=p.product_group_id,
        product_group_name=p.product_group.name if p.product_group else None,
        product_type_id=p.product_type_id,
        brand_id=p.brand_id,
        product_code=p.product_code,
        name=p.name,
        description=p.description,
        image_url=p.image_url,
        status=p.status,
        variants=[
            _public_variant_response(
                v,
                stock_by_variant.get(v.id, 0),
            )
            for v in variants
        ],
    )


def _format_inr(amount: Decimal) -> str:
    return f"{amount.quantize(Decimal('0.01')):,.2f}"


def _format_checkout_address(body: PublicCheckoutRequest) -> str:
    return ", ".join(
        part
        for part in [
            body.shipping_address,
            body.city,
            body.state,
            body.postal_code,
            body.country,
        ]
        if part
    )


def _format_whatsapp_message(
    *,
    order_id: str,
    customer_name: str,
    items: list[tuple[str, str, str, str, str | None, int]],
    total_amount: Decimal,
    address: str,
) -> str:
    item_lines = "\n".join(
        "\n".join(
            [
                f"- {name}",
                f"  SKU: {sku_code}",
                f"  Size: {size} | Color: {color} | Qty: {quantity}",
                f"  Picture: {image_url}" if image_url else "  Picture: Not uploaded yet",
            ]
        )
        for name, sku_code, size, color, image_url, quantity in items
    )
    return (
        "✨ New BeHazel'd Order ✨\n\n"
        f"*Order ID:* #{order_id}\n"
        f"*Buyer:* {customer_name}\n"
        f"*Address:* {address}\n\n"
        "Items:\n"
        f"{item_lines}\n\n"
        f"Total Amount: ₹{_format_inr(total_amount)}\n"
        "_Please confirm my order!_"
    )


def _get_or_create_public_customer(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    name: str,
    email: str | None,
    phone: str | None,
    address: str,
) -> Customer:
    customer = None
    if email:
        customer = db.scalar(
            select(Customer).where(
                Customer.tenant_id == tenant_id,
                func.lower(Customer.email) == email.lower(),
                Customer.is_active.is_(True),
            )
        )
    if customer is None and phone:
        customer = db.scalar(
            select(Customer).where(
                Customer.tenant_id == tenant_id,
                Customer.phone == phone,
                Customer.is_active.is_(True),
            )
        )
    if customer is not None:
        customer.name = name
        customer.email = email or customer.email
        customer.phone = phone or customer.phone
        customer.address = address
        db.flush()
        return customer
    return SalesRepository(db).create_customer(
        tenant_id=tenant_id,
        name=name,
        email=email,
        phone=phone,
        address=address,
    )


# ── Products ──────────────────────────────────────────────────────────────────

@router.get(
    "/{tenant_id}/products",
    response_model=PaginatedProductsResponse,
)
def list_public_products(
    tenant_id: uuid.UUID,
    response: Response,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    category_id: uuid.UUID | None = Query(default=None),
    search: str | None = Query(default=None, max_length=100),
    db: Session = Depends(get_db),
) -> PaginatedProductsResponse:
    """
    List active products for a tenant.

    Supports optional filtering by category and keyword search on name / code.
    Returns a paginated envelope with `total` count for the client to drive
    pagination controls.
    """
    repo = PublicRepository(db)
    _mark_uncached(response)
    products = repo.list_active_products(
        tenant_id,
        category_id=category_id,
        search=search,
        skip=skip,
        limit=limit,
    )
    total = repo.count_active_products(
        tenant_id, category_id=category_id, search=search
    )
    # Enrich each product with its active variants (second targeted query per product)
    items = []
    for p in products:
        variants = repo.list_active_variants_for_product(tenant_id, p.id)
        stock_by_variant = repo.available_stock_by_variant(
            tenant_id,
            [v.id for v in variants],
        )
        items.append(_public_product_response(p, variants, stock_by_variant))

    return PaginatedProductsResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=items,
    )


@router.get(
    "/{tenant_id}/products/{product_id}",
    response_model=PublicProductResponse,
)
def get_public_product(
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    response: Response,
    db: Session = Depends(get_db),
) -> PublicProductResponse:
    """Return a single active product with all its active variants."""
    _mark_uncached(response)
    from app.core.exceptions import NotFoundError
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.models.catalog import Product

    stmt = (
        select(Product)
        .options(
            selectinload(Product.category),
            selectinload(Product.product_group),
        )
        .where(
            Product.id == product_id,
            Product.tenant_id == tenant_id,
            Product.status == "active",
        )
    )
    product = db.execute(stmt).scalar_one_or_none()
    if product is None:
        raise NotFoundError(f"Product {product_id} not found")

    repo = PublicRepository(db)
    variants = repo.list_active_variants_for_product(tenant_id, product_id)
    stock_by_variant = repo.available_stock_by_variant(
        tenant_id,
        [v.id for v in variants],
    )

    return _public_product_response(product, variants, stock_by_variant)


# ── Checkout ─────────────────────────────────────────────────────────────────

@router.post(
    "/{tenant_id}/checkout",
    response_model=PublicCheckoutResponse,
    status_code=status.HTTP_201_CREATED,
)
def public_checkout(
    tenant_id: uuid.UUID,
    body: PublicCheckoutRequest,
    db: Session = Depends(get_db),
) -> PublicCheckoutResponse:
    """
    Save a storefront order as a confirmed sale before the customer is redirected
    to WhatsApp for human confirmation.
    """
    service = SalesService(db)
    service.ensure_sales_tables_available()
    InventoryService(db).ensure_inventory_tables_available()
    address = _format_checkout_address(body)

    summary_items: list[tuple[str, str, str, str, str | None, int]] = []
    line_requests: list[CreateSaleBillLineRequest] = []
    server_total = Decimal("0")

    for item in body.items:
        variant = db.scalar(
            select(ProductVariant)
            .options(
                selectinload(ProductVariant.product),
                selectinload(ProductVariant.size),
                selectinload(ProductVariant.color),
            )
            .where(
                ProductVariant.tenant_id == tenant_id,
                ProductVariant.id == item.product_variant_id,
                ProductVariant.status == "active",
            )
        )
        if variant is None:
            raise ValidationError(f"Variant {item.product_variant_id} is not available")
        quantity = Decimal(item.quantity)
        price = Decimal(str(variant.selling_price)).quantize(Decimal("0.01"))
        final_price = price_with_gst(price, date.today())
        server_total += (quantity * final_price).quantize(Decimal("0.01"))
        line_requests.append(
            CreateSaleBillLineRequest(
                product_variant_id=variant.id,
                quantity=quantity,
                selling_price=price,
                tax_rate=gst_rate_for(date.today()),
                discount_amount=Decimal("0"),
            )
        )
        summary_items.append(
            (
                variant.product.name,
                variant.sku_code,
                variant.size.name,
                variant.color.name,
                variant.image_url or variant.product.image_url,
                item.quantity,
            )
        )

    # Do not trust the browser for billing; use server prices. This accepts small
    # decimal/string formatting differences but rejects materially stale carts.
    if abs(server_total - body.total_amount) > Decimal("0.01"):
        raise ValidationError(
            f"Cart total changed. Expected ₹{_format_inr(server_total)}; received ₹{_format_inr(body.total_amount)}"
        )

    try:
        customer = _get_or_create_public_customer(
            db,
            tenant_id=tenant_id,
            name=body.customer_name,
            email=str(body.customer_email) if body.customer_email else None,
            phone=body.customer_phone,
            address=address,
        )
        location, bin_obj = service._default_sale_location_bin(tenant_id)
        sale_request = CreateSaleBillRequest(
            location_id=location.id,
            bin_id=bin_obj.id,
            bill_date=date.today(),
            customer_id=customer.id,
            notes=f"Website order via WhatsApp. Ship to: {address}",
            lines=line_requests,
            payment=CreateSalePaymentRequest(
                amount=server_total,
                payment_mode=SalePaymentMode.OTHER,
                notes="Website order pending WhatsApp confirmation/payment",
            ),
        )
        bill, _metadata = service.create_sale(
            tenant_id=tenant_id,
            req=sale_request,
        )
    except Exception:
        db.rollback()
        raise

    whatsapp_message = _format_whatsapp_message(
        order_id=bill.invoice_number,
        customer_name=body.customer_name,
        items=summary_items,
        total_amount=server_total,
        address=address,
    )
    return PublicCheckoutResponse(
        order_id=bill.invoice_number,
        total_amount=server_total,
        order_summary=whatsapp_message,
        whatsapp_message=whatsapp_message,
    )


# ── Categories ────────────────────────────────────────────────────────────────

@router.get(
    "/{tenant_id}/categories",
    response_model=list[PublicCategoryResponse],
)
def list_public_categories(
    tenant_id: uuid.UUID,
    response: Response,
    db: Session = Depends(get_db),
) -> list[PublicCategoryResponse]:
    """Return all active categories in sort_order for the storefront nav."""
    _mark_uncached(response)
    return PublicRepository(db).list_active_categories(tenant_id)  # type: ignore[return-value]


@router.get(
    "/{tenant_id}/product-groups",
    response_model=list[PublicProductGroupResponse],
)
def list_public_product_groups(
    tenant_id: uuid.UUID,
    response: Response,
    db: Session = Depends(get_db),
) -> list[PublicProductGroupResponse]:
    """Return all active product groups / collections for storefront grouping."""
    _mark_uncached(response)
    return PublicRepository(db).list_active_product_groups(tenant_id)  # type: ignore[return-value]


# ── Customer self-registration ────────────────────────────────────────────────

@router.post(
    "/{tenant_id}/customers/register",
    response_model=PublicCustomerResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_customer(
    tenant_id: uuid.UUID,
    body: PublicRegisterCustomerRequest,
    db: Session = Depends(get_db),
) -> PublicCustomerResponse:
    """
    Allow a customer to create their own profile.
    No authentication required — uses the SalesRepository directly.
    """
    try:
        customer = SalesRepository(db).create_customer(
            tenant_id=tenant_id,
            name=body.name,
            email=body.email,
            phone=body.phone,
            address=body.address,
        )
        db.commit()
        db.refresh(customer)
        return customer  # type: ignore[return-value]
    except Exception:
        db.rollback()
        raise
