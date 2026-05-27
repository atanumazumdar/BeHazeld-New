"""
PublicRepository — read-only catalog access for public (unauthenticated) endpoints.

Design rules
------------
* NO writes.  This class has no create/update/delete methods.
* Every method is tenant-scoped (tenant_id first arg).
* Only `status='active'` products and `is_active=True` categories are returned
  — soft-deleted records are invisible to public consumers.
* Queries use SQLAlchemy Core SELECT expressions (not Session.query()) for
  explicit, auditable SQL with no accidental lazy-load surprises.
* Optional filters (search, category_id) are applied with LIKE / equality;
  no ORM eager-loading on the variant relationship to keep queries lean.
"""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.catalog import Category, Product, ProductVariant


class PublicRepository:
    """
    Read-only data access for the public storefront API.
    Instantiate with the same Session used by the request; never commit.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Products ──────────────────────────────────────────────────────────────

    def list_active_products(
        self,
        tenant_id: uuid.UUID,
        *,
        category_id: uuid.UUID | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Product]:
        """
        Return active products for a tenant, optionally filtered by category
        and/or a name/code keyword search.  Results are ordered by name.

        Variants are NOT eagerly loaded here; the API layer calls
        `list_active_variants_for_product()` per product if needed, or the
        router returns only product-level data.
        """
        stmt = (
            select(Product)
            .where(
                Product.tenant_id == tenant_id,
                Product.status == "active",
            )
        )
        if category_id is not None:
            stmt = stmt.where(Product.category_id == category_id)
        if search:
            like = f"%{search}%"
            stmt = stmt.where(
                Product.name.ilike(like) | Product.product_code.ilike(like)
            )
        stmt = stmt.order_by(Product.name).offset(skip).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def count_active_products(
        self,
        tenant_id: uuid.UUID,
        *,
        category_id: uuid.UUID | None = None,
        search: str | None = None,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(Product)
            .where(
                Product.tenant_id == tenant_id,
                Product.status == "active",
            )
        )
        if category_id is not None:
            stmt = stmt.where(Product.category_id == category_id)
        if search:
            like = f"%{search}%"
            stmt = stmt.where(
                Product.name.ilike(like) | Product.product_code.ilike(like)
            )
        return self.db.execute(stmt).scalar_one()

    def list_active_variants_for_product(
        self, tenant_id: uuid.UUID, product_id: uuid.UUID
    ) -> list[ProductVariant]:
        """Return all active (non-deleted) variants for a given product."""
        stmt = (
            select(ProductVariant)
            .where(
                ProductVariant.tenant_id == tenant_id,
                ProductVariant.product_id == product_id,
                ProductVariant.status == "active",
            )
            .order_by(ProductVariant.sku_code)
        )
        return list(self.db.execute(stmt).scalars().all())

    def count_active_skus(self, tenant_id: uuid.UUID) -> int:
        """Count of all active SKUs — used for the dashboard metric."""
        stmt = (
            select(func.count())
            .select_from(ProductVariant)
            .where(
                ProductVariant.tenant_id == tenant_id,
                ProductVariant.status == "active",
            )
        )
        return self.db.execute(stmt).scalar_one()

    # ── Categories ────────────────────────────────────────────────────────────

    def list_active_categories(self, tenant_id: uuid.UUID) -> list[Category]:
        """
        Return all active categories ordered by sort_order then name.
        Hierarchy (parent/child) is not currently modelled in Category;
        all categories are returned flat for the public consumer to organise.
        """
        stmt = (
            select(Category)
            .where(
                Category.tenant_id == tenant_id,
                Category.is_active.is_(True),
            )
            .order_by(Category.sort_order, Category.name)
        )
        return list(self.db.execute(stmt).scalars().all())
