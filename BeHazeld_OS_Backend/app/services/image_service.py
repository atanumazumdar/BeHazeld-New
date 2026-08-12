from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import BinaryIO

from app.core.config import settings
from app.core.exceptions import ValidationError


ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


class ImageService:
    """Stores product imagery on the local server and returns public URLs."""

    def __init__(self) -> None:
        if settings.UPLOAD_STORAGE_PROVIDER.lower() != "local":
            raise ValidationError("Only local image storage is enabled on this server")

        self.upload_root = Path(settings.UPLOAD_LOCAL_PATH).expanduser().resolve()
        self.public_base_url = settings.PUBLIC_BASE_URL.rstrip("/")

    def upload_product_image(
        self,
        file: BinaryIO,
        *,
        tenant_id: uuid.UUID,
        product_id: uuid.UUID,
        filename: str | None = None,
    ) -> str:
        return self._save_image(
            file,
            relative_dir=Path(str(tenant_id)) / "products" / str(product_id),
            filename=filename,
            fallback_stem=str(product_id),
        )

    def upload_variant_image(
        self,
        file: BinaryIO,
        *,
        tenant_id: uuid.UUID,
        product_id: uuid.UUID,
        variant_id: uuid.UUID,
        filename: str | None = None,
    ) -> str:
        return self._save_image(
            file,
            relative_dir=Path(str(tenant_id)) / "products" / str(product_id) / "variants",
            filename=filename,
            fallback_stem=str(variant_id),
        )

    def _save_image(
        self,
        file: BinaryIO,
        *,
        relative_dir: Path,
        filename: str | None,
        fallback_stem: str,
    ) -> str:
        extension = self._safe_extension(filename)
        saved_name = f"{fallback_stem}{extension}"
        target_dir = self.upload_root / relative_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        target_path = target_dir / saved_name
        file.seek(0)
        with target_path.open("wb") as output:
            shutil.copyfileobj(file, output)

        public_path = "/".join(["uploads", *relative_dir.parts, saved_name])
        return f"{self.public_base_url}/{public_path}"

    def _safe_extension(self, filename: str | None) -> str:
        extension = Path(filename or "").suffix.lower()
        if not extension:
            extension = ".jpg"
        if extension not in ALLOWED_IMAGE_EXTENSIONS:
            raise ValidationError("Unsupported image file type")
        return extension
