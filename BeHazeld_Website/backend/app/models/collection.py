from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Collection(Base):
    """
    Editorial grouping of products — e.g. 'Campus Muse', 'Power Edit'.
    Adding a Collection row and assigning products to it is the *only*
    action needed to make a new page appear on the frontend.
    """

    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    hero_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Simple relationship — active-product filtering is done in queries, not here
    products: Mapped[list["Product"]] = relationship(  # type: ignore[name-defined]
        back_populates="collection",
        order_by="Product.id",
        lazy="select",
    )
