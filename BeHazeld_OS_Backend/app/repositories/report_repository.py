"""
ReportRepository — optimised aggregate queries for the business dashboard.

Design rules
------------
* ALL queries use SQLAlchemy Core aggregations (SUM, COUNT) — no Python-side
  accumulation over large row sets.
* Every method is tenant-scoped (tenant_id as first arg).
* Methods return lightweight dataclass-like dicts or typed tuples, not ORM
  objects, to keep the response layer decoupled from the ORM model graph.
"""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, func, select
from sqlalchemy.orm import Session

from app.models.catalog import ProductVariant
from app.models.inventory import StockBalance
from app.models.purchase import PurchaseBill
from app.models.sales import SaleBill, SaleBillLine


class ReportRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Revenue & COGS ────────────────────────────────────────────────────────

    def get_total_revenue(
        self,
        tenant_id: uuid.UUID,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> Decimal:
        """SUM(total_amount) from confirmed sale_bills, optionally date-filtered."""
        stmt = (
            select(func.coalesce(func.sum(SaleBill.total_amount), 0))
            .where(
                SaleBill.tenant_id == tenant_id,
                SaleBill.status == "confirmed",
            )
        )
        if from_date:
            stmt = stmt.where(SaleBill.bill_date >= from_date)
        if to_date:
            stmt = stmt.where(SaleBill.bill_date <= to_date)
        return Decimal(str(self.db.execute(stmt).scalar_one()))

    def get_total_purchase_cost(
        self,
        tenant_id: uuid.UUID,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> Decimal:
        """
        SUM(total_amount) from confirmed purchase_bills.
        Used as a proxy for COGS (purchase cost ≈ cost of goods received).
        """
        stmt = (
            select(func.coalesce(func.sum(PurchaseBill.total_amount), 0))
            .where(
                PurchaseBill.tenant_id == tenant_id,
                PurchaseBill.status == "confirmed",
            )
        )
        if from_date:
            stmt = stmt.where(PurchaseBill.bill_date >= from_date)
        if to_date:
            stmt = stmt.where(PurchaseBill.bill_date <= to_date)
        return Decimal(str(self.db.execute(stmt).scalar_one()))

    def get_total_cogs(
        self,
        tenant_id: uuid.UUID,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> Decimal:
        """
        SUM(quantity * unit cost) for confirmed sale lines.

        Older sale rows may have unit_cost saved as 0, so fall back to the
        current variant cost_price for dashboard reporting.
        """
        cost_expr = func.coalesce(
            func.nullif(SaleBillLine.unit_cost, 0),
            ProductVariant.cost_price,
            0,
        )
        stmt = (
            select(func.coalesce(func.sum(SaleBillLine.quantity * cost_expr), 0))
            .join(SaleBill, SaleBillLine.bill_id == SaleBill.id)
            .join(ProductVariant, SaleBillLine.product_variant_id == ProductVariant.id)
            .where(
                SaleBill.tenant_id == tenant_id,
                SaleBill.status == "confirmed",
            )
        )
        if from_date:
            stmt = stmt.where(SaleBill.bill_date >= from_date)
        if to_date:
            stmt = stmt.where(SaleBill.bill_date <= to_date)
        return Decimal(str(self.db.execute(stmt).scalar_one()))

    # ── Tax (GST) ─────────────────────────────────────────────────────────────

    def get_gst_summary(
        self,
        tenant_id: uuid.UUID,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> dict:
        """
        Return GST totals for a date range.

        Returns
        -------
        {
            "sales_tax_collected": Decimal,   # tax collected on outward supply
            "purchase_tax_paid":   Decimal,   # input tax credit (ITC)
            "net_gst_payable":     Decimal,   # payable = collected - ITC
        }
        """
        # Outward supply — tax collected from customers
        sale_stmt = (
            select(func.coalesce(func.sum(SaleBill.tax_amount), 0))
            .where(
                SaleBill.tenant_id == tenant_id,
                SaleBill.status == "confirmed",
            )
        )
        if from_date:
            sale_stmt = sale_stmt.where(SaleBill.bill_date >= from_date)
        if to_date:
            sale_stmt = sale_stmt.where(SaleBill.bill_date <= to_date)
        sales_tax = Decimal(str(self.db.execute(sale_stmt).scalar_one()))

        # Inward supply — tax paid to vendors (input tax credit)
        purchase_stmt = (
            select(func.coalesce(func.sum(PurchaseBill.tax_amount), 0))
            .where(
                PurchaseBill.tenant_id == tenant_id,
                PurchaseBill.status == "confirmed",
            )
        )
        if from_date:
            purchase_stmt = purchase_stmt.where(PurchaseBill.bill_date >= from_date)
        if to_date:
            purchase_stmt = purchase_stmt.where(PurchaseBill.bill_date <= to_date)
        purchase_tax = Decimal(str(self.db.execute(purchase_stmt).scalar_one()))

        return {
            "sales_tax_collected": sales_tax,
            "purchase_tax_paid":   purchase_tax,
            "net_gst_payable":     sales_tax - purchase_tax,
        }

    # ── Low-stock alert ───────────────────────────────────────────────────────

    def get_low_stock_variants(
        self, tenant_id: uuid.UUID
    ) -> list[dict]:
        """
        Return variants where SUM(quantity_on_hand) across all locations is
        ≤ reorder_level.

        The join aggregates balances per variant so multi-location stock is
        summed before comparing to the threshold.

        Returns list of dicts with keys:
            variant_id, sku_code, product_id, reorder_level, total_on_hand
        """
        # Aggregate total on_hand per variant across all locations
        balance_sub = (
            select(
                StockBalance.product_variant_id,
                func.sum(StockBalance.quantity_on_hand).label("total_on_hand"),
            )
            .where(StockBalance.tenant_id == tenant_id)
            .group_by(StockBalance.product_variant_id)
            .subquery()
        )

        stmt = (
            select(
                ProductVariant.id.label("variant_id"),
                ProductVariant.sku_code,
                ProductVariant.product_id,
                ProductVariant.reorder_level,
                func.coalesce(balance_sub.c.total_on_hand, 0).label("total_on_hand"),
            )
            .outerjoin(
                balance_sub,
                ProductVariant.id == balance_sub.c.product_variant_id,
            )
            .where(
                ProductVariant.tenant_id == tenant_id,
                ProductVariant.status == "active",
                func.coalesce(balance_sub.c.total_on_hand, 0)
                <= ProductVariant.reorder_level,
            )
            .order_by(ProductVariant.sku_code)
        )

        rows = self.db.execute(stmt).all()
        return [
            {
                "variant_id":    row.variant_id,
                "sku_code":      row.sku_code,
                "product_id":    row.product_id,
                "reorder_level": row.reorder_level,
                "total_on_hand": Decimal(str(row.total_on_hand)),
            }
            for row in rows
        ]

    # ── Active SKU count (dashboard) ──────────────────────────────────────────

    def count_active_skus(self, tenant_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(ProductVariant)
            .where(
                ProductVariant.tenant_id == tenant_id,
                ProductVariant.status == "active",
            )
        )
        return self.db.execute(stmt).scalar_one()
