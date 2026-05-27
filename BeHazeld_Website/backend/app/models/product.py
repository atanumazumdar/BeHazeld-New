from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Product(Base):
    """
    Root product entity.

    Old flat columns (category, image_url, color, size, inventory_count,
    price) have been removed and replaced by:
        - collection_id  → Collection (hierarchy)
        - images         → ProductImage  (one-to-many photos)
        - variants       → ProductVariant (size/colour/stock/SKU)
        - base_price     → replaces price; final price = base_price + variant.price_adjustment
    """

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    collection_id: Mapped[int | None] = mapped_column(
        ForeignKey("collections.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    base_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # ── Relationships ────────────────────────────────────────────────
    collection: Mapped["Collection"] = relationship(  # type: ignore[name-defined]
        back_populates="products",
        lazy="select",
    )
    images: Mapped[list["ProductImage"]] = relationship(  # type: ignore[name-defined]
        back_populates="product",
        order_by="ProductImage.display_order",
        cascade="all, delete-orphan",
        lazy="select",
    )
    variants: Mapped[list["ProductVariant"]] = relationship(  # type: ignore[name-defined]
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="select",
    )

    # ── Convenience helpers ──────────────────────────────────────────
    @property
    def primary_image(self) -> "ProductImage | None":  # type: ignore[name-defined]
        for img in self.images:
            if img.is_primary:
                return img
        return self.images[0] if self.images else None

    @property
    def secondary_image(self) -> "ProductImage | None":  # type: ignore[name-defined]
        """Return the second image in display_order (the one after primary)."""
        primary = self.primary_image
        for img in self.images:
            if img is not primary:
                return img
        return None

    @property
    def min_price(self) -> Decimal:
        if not self.variants:
            return self.base_price
        available = [v for v in self.variants if v.is_available]
        if not available:
            return self.base_price
        return min(self.base_price + v.price_adjustment for v in available)

    @property
    def total_stock(self) -> int:
        return sum(v.stock_count for v in self.variants)
