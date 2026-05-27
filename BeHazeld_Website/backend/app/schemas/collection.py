from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.product import ProductRead


# ── Collection summary (nav / listing) ───────────────────────────────
class CollectionRead(BaseModel):
    """Lightweight view — used in nav and collection index page."""

    id: int
    name: str
    slug: str
    description: str
    hero_image_url: str | None
    display_order: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Collection with its products ─────────────────────────────────────
class CollectionWithProducts(CollectionRead):
    """
    Full view returned by GET /collections/{slug}.

    The frontend uses this to render a dynamic collection page:
    adding a product to the DB with this collection's id is the
    *only* step needed to make it appear on the page.
    """

    products: list[ProductRead]

    model_config = ConfigDict(from_attributes=True)
