# Import every model here so Alembic's env.py sees all tables when it
# does `from app.models import Base`.  Order: parents before children.
from app.models.collection import Collection            # noqa: F401
from app.models.product import Product                  # noqa: F401
from app.models.product_image import ProductImage       # noqa: F401
from app.models.product_variant import ProductVariant   # noqa: F401
from app.models.order import Order, OrderItem           # noqa: F401
from app.database import Base                           # noqa: F401

__all__ = [
    "Base",
    "Collection",
    "Product",
    "ProductImage",
    "ProductVariant",
    "Order",
    "OrderItem",
]
