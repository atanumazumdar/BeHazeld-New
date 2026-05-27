from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.schemas.order import CheckoutCreate, OrderRead

router = APIRouter(prefix="/checkout", tags=["checkout"])

SHIPPING_TOTAL = Decimal("0.00")


@router.post("/", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def create_checkout(payload: CheckoutCreate, db: Session = Depends(get_db)) -> Order:
    """
    Place an order.

    For each item:
    - If variant_id is provided → use that variant for stock decrement + pricing
    - If variant_id is None → use product.base_price and skip variant stock check
      (legacy path; the frontend will always send variant_id after Phase I)
    """
    subtotal = Decimal("0.00")
    order_items: list[OrderItem] = []

    for item in payload.items:
        # ── Validate product ─────────────────────────────────────────
        product = db.scalar(
            select(Product).where(
                Product.id == item.product_id,
                Product.is_active.is_(True),
            )
        )
        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product {item.product_id} was not found",
            )

        # ── Resolve variant ──────────────────────────────────────────
        if item.variant_id is not None:
            variant = db.scalar(
                select(ProductVariant).where(
                    ProductVariant.id == item.variant_id,
                    ProductVariant.product_id == item.product_id,
                    ProductVariant.is_available.is_(True),
                )
            )
            if variant is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Variant {item.variant_id} not found for product {item.product_id}",
                )
            if variant.stock_count < item.quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Only {variant.stock_count} units of '{product.name}' "
                           f"({variant.color} / {variant.size}) available",
                )
            unit_price = product.base_price + variant.price_adjustment
            color = variant.color
            size  = variant.size

            # Decrement variant stock
            variant.stock_count -= item.quantity
            if variant.stock_count == 0:
                variant.is_available = False

        else:
            # Legacy path — no variant selected
            unit_price = product.base_price
            color = "—"
            size  = "—"
            variant = None

        line_total = unit_price * item.quantity
        subtotal  += line_total

        order_items.append(
            OrderItem(
                product_id=product.id,
                product_name=product.name,
                product_slug=product.slug,
                variant_id=variant.id if variant else None,
                color=color,
                size=size,
                unit_price=unit_price,
                quantity=item.quantity,
                line_total=line_total,
            )
        )

    order = Order(
        customer_email=payload.customer_email,
        customer_name=payload.customer_name,
        shipping_address=payload.shipping_address,
        city=payload.city,
        state=payload.state,
        postal_code=payload.postal_code,
        country=payload.country,
        subtotal=subtotal,
        shipping_total=SHIPPING_TOTAL,
        total=subtotal + SHIPPING_TOTAL,
        items=order_items,
    )

    db.add(order)
    db.commit()

    return db.scalar(
        select(Order)
        .where(Order.id == order.id)
        .options(selectinload(Order.items))
    )
