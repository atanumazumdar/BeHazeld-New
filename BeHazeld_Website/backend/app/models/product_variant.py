from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ProductVariant(Base):
    """
    Each buyable size/colour combination of a product.

    Final customer price = product.base_price + variant.price_adjustment
    (adjustment is typically 0.00; use a positive value for premium sizes
    or a negative value for sale variants without touching base_price).

    stock_count is decremented by the checkout router when an order is placed.
    """

    __tablename__ = "product_variants"
    __table_args__ = (
        UniqueConstraint("product_id", "color", "size", name="uq_variant_product_color_size"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sku: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    color: Mapped[str] = mapped_column(String(60), nullable=False)
    size: Mapped[str] = mapped_column(String(40), nullable=False)
    price_adjustment: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00"), nullable=False
    )
    stock_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    product: Mapped["Product"] = relationship(back_populates="variants")  # type: ignore[name-defined]
