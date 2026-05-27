"""
Cloudinary integration — upload, delete, and URL transformation helpers.

Configuration (via .env):
    CLOUDINARY_CLOUD_NAME
    CLOUDINARY_API_KEY
    CLOUDINARY_API_SECRET

Folder structure on Cloudinary:
    behazeld/
    ├── products/{product_slug}/          ← product photos
    └── collections/{collection_slug}/    ← collection hero images

URL transformation presets (applied at fetch time — no extra storage):
    card     : 400×533  crop=fill  f=auto q=auto   (product card thumbnail)
    detail   : 900×1200 crop=fill  f=auto q=auto   (product detail hero)
    hero     : 1440×600 crop=fill  f=auto q=auto   (collection banner)
    original : f=auto q=auto                        (full quality)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

import cloudinary
import cloudinary.uploader


# ── Allowed MIME types ────────────────────────────────────────────────
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/gif",
}
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# ── Transformation presets ────────────────────────────────────────────
# Applied as URL path segments: /c_fill,w_400,h_533,f_auto,q_auto/
TRANSFORMS: dict[str, str] = {
    "card":     "c_fill,w_400,h_533,f_auto,q_auto",
    "detail":   "c_fill,w_900,h_1200,f_auto,q_auto",
    "hero":     "c_fill,w_1440,h_600,f_auto,q_auto",
    "original": "f_auto,q_auto",
}


# ── Client initialisation (lazy — only when first upload is attempted) ─
def _configure() -> bool:
    """
    Configure the Cloudinary SDK from env vars.
    Returns True if credentials are present, False otherwise.
    """
    cloud_name  = os.getenv("CLOUDINARY_CLOUD_NAME")
    api_key     = os.getenv("CLOUDINARY_API_KEY")
    api_secret  = os.getenv("CLOUDINARY_API_SECRET")

    if not all([cloud_name, api_key, api_secret]):
        return False

    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
        secure=True,
    )
    return True


# ── Result dataclass ──────────────────────────────────────────────────
@dataclass
class UploadResult:
    """Structured result from a Cloudinary upload."""
    public_id:  str         # Cloudinary public_id (path within cloud)
    secure_url: str         # Full HTTPS CDN URL (stored in DB)
    width:      int
    height:     int
    format:     str
    bytes:      int

    def transform_url(self, preset: Literal["card", "detail", "hero", "original"] = "original") -> str:
        """
        Return the CDN URL with the given transformation applied.

        Example:
            result.transform_url("card")
            → https://res.cloudinary.com/<cloud>/image/upload/c_fill,w_400,h_533,f_auto,q_auto/behazeld/products/ivory-bloom/primary.jpg
        """
        transform_string = TRANSFORMS.get(preset, TRANSFORMS["original"])
        # Insert the transformation segment after '/upload/'
        return self.secure_url.replace("/upload/", f"/upload/{transform_string}/", 1)


# ── Upload helpers ────────────────────────────────────────────────────
def _upload(
    file_bytes: bytes,
    public_id:  str,
    *,
    eager_transforms: bool = True,
) -> UploadResult:
    """
    Core upload function — sends bytes to Cloudinary, returns UploadResult.
    Raises RuntimeError if Cloudinary is not configured.
    """
    if not _configure():
        raise RuntimeError(
            "Cloudinary is not configured. Set CLOUDINARY_CLOUD_NAME, "
            "CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET in your .env file."
        )

    kwargs: dict = {
        "public_id":     public_id,
        "overwrite":     True,
        "resource_type": "image",
        # Let Cloudinary choose the best format (WebP on supporting browsers)
        "format":        "",
        "quality":       "auto",
    }

    if eager_transforms:
        # Pre-generate card + detail sizes so the CDN has them cached immediately
        kwargs["eager"] = [
            {"transformation": TRANSFORMS["card"]},
            {"transformation": TRANSFORMS["detail"]},
        ]
        kwargs["eager_async"] = True

    result = cloudinary.uploader.upload(file_bytes, **kwargs)

    return UploadResult(
        public_id  = result["public_id"],
        secure_url = result["secure_url"],
        width      = result["width"],
        height     = result["height"],
        format     = result.get("format", ""),
        bytes      = result.get("bytes", 0),
    )


def upload_product_image(
    file_bytes:    bytes,
    product_slug:  str,
    display_order: int = 0,
    is_primary:    bool = False,
) -> UploadResult:
    """
    Upload a product photo.

    Folder:    behazeld/products/{product_slug}/
    Filename:  primary  (if is_primary) or  img-{display_order:02d}
    """
    filename  = "primary" if is_primary else f"img-{display_order:02d}"
    public_id = f"behazeld/products/{product_slug}/{filename}"
    return _upload(file_bytes, public_id)


def upload_collection_hero(
    file_bytes:      bytes,
    collection_slug: str,
) -> UploadResult:
    """
    Upload a collection hero banner.

    Folder:   behazeld/collections/{collection_slug}/
    Filename: hero
    """
    public_id = f"behazeld/collections/{collection_slug}/hero"
    return _upload(file_bytes, public_id, eager_transforms=False)


def delete_image(public_id: str) -> bool:
    """
    Delete an image from Cloudinary by public_id.
    Returns True on success, False if not configured or not found.
    """
    if not _configure():
        return False
    result = cloudinary.uploader.destroy(public_id)
    return result.get("result") == "ok"


# ── URL helpers (no Cloudinary call needed) ───────────────────────────
def build_transform_url(secure_url: str, preset: str = "original") -> str:
    """
    Given a stored secure_url, return a transformed version.
    Works without making any API call — just rewrites the URL string.
    """
    transform_string = TRANSFORMS.get(preset, TRANSFORMS["original"])
    return secure_url.replace("/upload/", f"/upload/{transform_string}/", 1)


def transform_urls_for(secure_url: str) -> dict[str, str]:
    """Return all preset URLs for a stored image URL."""
    return {preset: build_transform_url(secure_url, preset) for preset in TRANSFORMS}
