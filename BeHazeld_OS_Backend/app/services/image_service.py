from __future__ import annotations

import uuid
from typing import BinaryIO

import cloudinary
import cloudinary.uploader

from app.core.config import settings
from app.core.exceptions import ValidationError


class ImageService:
    """Uploads product imagery to Cloudinary and returns public HTTPS URLs."""

    def __init__(self) -> None:
        if not (
            settings.CLOUDINARY_CLOUD_NAME
            and settings.CLOUDINARY_API_KEY
            and settings.CLOUDINARY_API_SECRET
        ):
            raise ValidationError("Cloudinary credentials are not configured")

        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True,
        )

    def upload_product_image(
        self,
        file: BinaryIO,
        *,
        tenant_id: uuid.UUID,
        product_id: uuid.UUID,
        filename: str | None = None,
    ) -> str:
        public_id = f"{product_id}"
        if filename:
            public_id = f"{product_id}-{filename.rsplit('.', 1)[0]}"

        result = cloudinary.uploader.upload(
            file,
            folder=f"behazeld/{tenant_id}/products",
            public_id=public_id,
            overwrite=True,
            resource_type="image",
        )
        secure_url = result.get("secure_url")
        if not secure_url:
            raise ValidationError("Cloudinary upload did not return a secure URL")
        return str(secure_url)

    def upload_variant_image(
        self,
        file: BinaryIO,
        *,
        tenant_id: uuid.UUID,
        product_id: uuid.UUID,
        variant_id: uuid.UUID,
        filename: str | None = None,
    ) -> str:
        public_id = f"{variant_id}"
        if filename:
            public_id = f"{variant_id}-{filename.rsplit('.', 1)[0]}"

        result = cloudinary.uploader.upload(
            file,
            folder=f"behazeld/{tenant_id}/products/{product_id}/variants",
            public_id=public_id,
            overwrite=True,
            resource_type="image",
        )
        secure_url = result.get("secure_url")
        if not secure_url:
            raise ValidationError("Cloudinary upload did not return a secure URL")
        return str(secure_url)
