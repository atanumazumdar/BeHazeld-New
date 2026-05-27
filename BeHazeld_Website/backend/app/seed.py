"""
Seed script — populates the database with collections, products,
placeholder images, and size variants.

Run from the backend/ directory:
    python -m app.seed

Idempotent: rows are skipped if their slug already exists.

Placeholder images use placehold.co so each slot is visibly labelled
"Pic 1", "Pic 2" … on the frontend until real Cloudinary photos are
uploaded via the admin portal.

Sizes use standard Indian numeric sizing: 32, 34, 36, 38, 40, 42, 44, 46, 48.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models.collection import Collection
from app.models.product import Product
from app.models.product_image import ProductImage
from app.models.product_variant import ProductVariant


# ── Placeholder image helper ─────────────────────────────────────────
# Generates a warm-cream labelled placeholder for each product slot.
# Replace via the admin upload form when real photos are ready.
def _ph(n: int) -> str:
    """placehold.co URL labelled 'Pic N' in the brand cream/amber palette."""
    return f"https://placehold.co/400x533/D8CEBC/7A5C14/png?text=Pic+{n}&font=playfair-display"


# ── Standard sizes ───────────────────────────────────────────────────
SIZES = ["32", "34", "36", "38", "40", "42", "44", "46", "48"]


def _variants(sku_prefix: str, color: str, stock: int = 20) -> list[dict]:
    """Generate one variant per standard size for a given colour."""
    return [
        {
            "sku":              f"{sku_prefix}-{color[:3].upper()}-{size}",
            "color":           color,
            "size":            size,
            "price_adjustment": Decimal("0.00"),
            "stock_count":     stock,
        }
        for size in SIZES
    ]


# ── Collections ──────────────────────────────────────────────────────
SEED_COLLECTIONS = [
    {
        "name":           "Campus Muse",
        "slug":           "campus-muse",
        "description":    "Effortless. Expressive. Unapologetically You. Where comfort meets quiet confidence.",
        "hero_image_url": "/campus-muse-new.png",
        "display_order":  1,
    },
    {
        "name":           "Power Edit",
        "slug":           "power-edit",
        "description":    "Tailored for ambition. Styled for impact. Because presence is your power move.",
        "hero_image_url": "/power-edit.png",
        "display_order":  2,
    },
    {
        "name":           "Afterglow Evenings",
        "slug":           "afterglow-evenings",
        "description":    "Turn moments into statements. Soft lights. Strong impressions.",
        "hero_image_url": "/afterglow-evenings-new.png",
        "display_order":  3,
    },
    {
        "name":           "Ultra Luxe",
        "slug":           "ultra-luxe",
        "description":    "For the woman who commands every room. Couture craftsmanship without compromise.",
        "hero_image_url": None,
        "display_order":  4,
    },
    {
        "name":           "Accessories",
        "slug":           "accessories",
        "description":    "The finishing touch that defines the look. Handcrafted adornments for every silhouette.",
        "hero_image_url": None,
        "display_order":  5,
    },
    {
        "name":           "Pre Loved",
        "slug":           "pre-loved",
        "description":    "Sustainably yours. Uniquely Hazel. Curated pre-owned pieces in pristine condition.",
        "hero_image_url": None,
        "display_order":  6,
    },
]


# ── Products ─────────────────────────────────────────────────────────
# Each collection gets 4 products to fill one full row of the 4-column grid.
# Placeholder images are labelled Pic 1 … Pic 4 per collection.

SEED_PRODUCTS = [

    # ══ Campus Muse — Pic 1 ════════════════════════════════════════════
    {
        "collection_slug": "campus-muse",
        "name":       "Ivory Bloom Chikankari Kurta",
        "slug":       "ivory-bloom-chikankari-kurta",
        "description": "Hand-embroidered ivory cotton chikankari with delicate floral motifs. Paired with straight-cut palazzo for an effortless campus look.",
        "base_price":  Decimal("8500.00"),
        "images": [{"url": _ph(1), "alt_text": "Ivory Bloom Chikankari Kurta — front view", "is_primary": True}],
        "variants": _variants("CM-IBC", "Ivory", stock=20),
    },

    # ══ Campus Muse — Pic 2 ════════════════════════════════════════════
    {
        "collection_slug": "campus-muse",
        "name":       "Sage Green Kurta Set",
        "slug":       "sage-green-kurta-set",
        "description": "Breathable sage green cotton kurta with subtle thread work. A quiet statement for every seminar, library run, and coffee date.",
        "base_price":  Decimal("7200.00"),
        "images": [{"url": _ph(2), "alt_text": "Sage Green Kurta Set — full view", "is_primary": True}],
        "variants": _variants("CM-SGK", "Sage Green", stock=20),
    },

    # ══ Campus Muse — Pic 3 ════════════════════════════════════════════
    {
        "collection_slug": "campus-muse",
        "name":       "Dusty Rose Anarkali",
        "slug":       "dusty-rose-anarkali",
        "description": "A flared anarkali in dusty rose with fine mirror embroidery at the yoke. Moves beautifully. Remembers every room.",
        "base_price":  Decimal("11500.00"),
        "images": [{"url": _ph(3), "alt_text": "Dusty Rose Anarkali — flare detail", "is_primary": True}],
        "variants": _variants("CM-DRA", "Dusty Rose", stock=15),
    },

    # ══ Campus Muse — Pic 4 ════════════════════════════════════════════
    {
        "collection_slug": "campus-muse",
        "name":       "Indigo Block Print Suit",
        "slug":       "indigo-block-print-suit",
        "description": "Handblock-printed indigo cambric three-piece suit. Earthy, expressive, unapologetically you.",
        "base_price":  Decimal("9800.00"),
        "images": [{"url": _ph(4), "alt_text": "Indigo Block Print Suit — set view", "is_primary": True}],
        "variants": _variants("CM-IBP", "Indigo", stock=18),
    },

    # ══ Power Edit — Pic 1 ═════════════════════════════════════════════
    {
        "collection_slug": "power-edit",
        "name":       "Antique Gold Anarkali",
        "slug":       "antique-gold-anarkali",
        "description": "Floor-length anarkali in burnt gold tissue with a trail that moves like liquid light. The neckline is hand-finished with antique pearl buttons.",
        "base_price":  Decimal("28000.00"),
        "images": [{"url": _ph(1), "alt_text": "Antique Gold Anarkali — full length", "is_primary": True}],
        "variants": _variants("PE-AGA", "Antique Gold", stock=12),
    },

    # ══ Power Edit — Pic 2 ═════════════════════════════════════════════
    {
        "collection_slug": "power-edit",
        "name":       "Navy Blazer Lehenga",
        "slug":       "navy-blazer-lehenga",
        "description": "Structured navy crepe blazer paired with a flared lehenga skirt. The boardroom meets the banquet — without compromise.",
        "base_price":  Decimal("32000.00"),
        "images": [{"url": _ph(2), "alt_text": "Navy Blazer Lehenga — ensemble view", "is_primary": True}],
        "variants": _variants("PE-NBL", "Navy", stock=10),
    },

    # ══ Power Edit — Pic 3 ═════════════════════════════════════════════
    {
        "collection_slug": "power-edit",
        "name":       "Burgundy Silk Pant Suit",
        "slug":       "burgundy-silk-pant-suit",
        "description": "Raw silk jacket and wide-leg trousers in deep burgundy. Presence is the policy.",
        "base_price":  Decimal("24500.00"),
        "images": [{"url": _ph(3), "alt_text": "Burgundy Silk Pant Suit — front view", "is_primary": True}],
        "variants": _variants("PE-BSP", "Burgundy", stock=14),
    },

    # ══ Power Edit — Pic 4 ═════════════════════════════════════════════
    {
        "collection_slug": "power-edit",
        "name":       "Emerald Indo-Western Co-ord",
        "slug":       "emerald-indo-western-coord",
        "description": "Emerald green crop-top with zari trim and matching flared trousers. Impact without effort.",
        "base_price":  Decimal("19800.00"),
        "images": [{"url": _ph(4), "alt_text": "Emerald Indo-Western Co-ord — set view", "is_primary": True}],
        "variants": _variants("PE-EIW", "Emerald", stock=16),
    },

    # ══ Afterglow Evenings — Pic 1 ═════════════════════════════════════
    {
        "collection_slug": "afterglow-evenings",
        "name":       "Heritage Kanjivaram Saree",
        "slug":       "heritage-kanjivaram-saree",
        "description": "A Kanjivaram saree woven on handlooms in Varanasi. The deep palette is contrasted with a gold zari border — designed to be passed down.",
        "base_price":  Decimal("89000.00"),
        "images": [{"url": _ph(1), "alt_text": "Heritage Kanjivaram Saree — drape detail", "is_primary": True}],
        "variants": _variants("AE-HKS", "Mahogany", stock=10),
    },

    # ══ Afterglow Evenings — Pic 2 ═════════════════════════════════════
    {
        "collection_slug": "afterglow-evenings",
        "name":       "Champagne Zari Set",
        "slug":       "champagne-zari-set",
        "description": "A refined occasion set with champagne zari accents and an easy evening silhouette. Arrives as a three-piece ensemble.",
        "base_price":  Decimal("67000.00"),
        "images": [{"url": _ph(2), "alt_text": "Champagne Zari Set — ensemble view", "is_primary": True}],
        "variants": _variants("AE-CZS", "Champagne", stock=12),
    },

    # ══ Afterglow Evenings — Pic 3 ═════════════════════════════════════
    {
        "collection_slug": "afterglow-evenings",
        "name":       "Midnight Blue Tissue Saree",
        "slug":       "midnight-blue-tissue-saree",
        "description": "Midnight blue tissue silk with scattered Swarovski sequins. The kind of saree that turns chandelier light into a personal spotlight.",
        "base_price":  Decimal("54000.00"),
        "images": [{"url": _ph(3), "alt_text": "Midnight Blue Tissue Saree — full drape", "is_primary": True}],
        "variants": _variants("AE-MBT", "Midnight Blue", stock=8),
    },

    # ══ Afterglow Evenings — Pic 4 ═════════════════════════════════════
    {
        "collection_slug": "afterglow-evenings",
        "name":       "Rose Gold Sharara Set",
        "slug":       "rose-gold-sharara-set",
        "description": "Gossamer rose gold sharara with a sheer embroidered cape. Soft lights. Strong impressions.",
        "base_price":  Decimal("48000.00"),
        "images": [{"url": _ph(4), "alt_text": "Rose Gold Sharara Set — cape detail", "is_primary": True}],
        "variants": _variants("AE-RGS", "Rose Gold", stock=10),
    },
]


# ════════════════════════════════════════════════════════════════════
def seed() -> None:
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:

        # ── 1. Collections ───────────────────────────────────────────
        for col_data in SEED_COLLECTIONS:
            if db.scalar(select(Collection).where(Collection.slug == col_data["slug"])):
                print(f"  [skip] collection: {col_data['slug']}")
                continue
            db.add(Collection(**col_data))
            print(f"  [add]  collection: {col_data['slug']}")

        db.commit()

        coll_id_by_slug = {
            c.slug: c.id
            for c in db.scalars(select(Collection)).all()
        }

        # ── 2. Products, images, variants ────────────────────────────
        for prod_data in SEED_PRODUCTS:
            if db.scalar(select(Product).where(Product.slug == prod_data["slug"])):
                print(f"  [skip] product:     {prod_data['slug']}")
                continue

            coll_id = coll_id_by_slug.get(prod_data["collection_slug"])
            if not coll_id:
                print(f"  [warn] unknown collection '{prod_data['collection_slug']}' — skipping")
                continue

            product = Product(
                collection_id=coll_id,
                name=prod_data["name"],
                slug=prod_data["slug"],
                description=prod_data["description"],
                base_price=prod_data["base_price"],
            )
            db.add(product)
            db.flush()

            for i, img in enumerate(prod_data["images"]):
                db.add(ProductImage(product_id=product.id, display_order=i, **img))

            for v in prod_data["variants"]:
                db.add(ProductVariant(product_id=product.id, is_available=True, **v))

            print(f"  [add]  product:     {prod_data['slug']} "
                  f"({len(prod_data['images'])} imgs · {len(prod_data['variants'])} variants)")

        db.commit()

    print("\n✓ Seed complete.")


if __name__ == "__main__":
    print("Seeding BeHAZEL'd database…\n")
    seed()
