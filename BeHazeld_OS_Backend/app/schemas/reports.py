"""
Report and dashboard Pydantic schemas.
"""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class DashboardMetrics(BaseModel):
    """Top-level summary for the owner's dashboard."""
    total_revenue:    Decimal
    total_cogs:       Decimal       # total purchase cost as COGS proxy
    gross_profit:     Decimal       # revenue - cogs
    total_tax_collected: Decimal    # GST collected on sales
    active_skus:      int


class LowStockItem(BaseModel):
    variant_id:    uuid.UUID
    sku_code:      str
    product_id:    uuid.UUID
    reorder_level: int
    total_on_hand: Decimal


class GstSummary(BaseModel):
    from_date:            date | None
    to_date:              date | None
    sales_tax_collected:  Decimal
    purchase_tax_paid:    Decimal
    net_gst_payable:      Decimal
