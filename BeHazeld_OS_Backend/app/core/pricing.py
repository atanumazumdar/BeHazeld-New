"""Business pricing rules shared by purchases, sales, and stock valuation."""
from datetime import date
from decimal import Decimal

GST_EFFECTIVE_DATE = date(2026, 9, 1)
GST_RATE = Decimal("0.05")
NO_GST = Decimal("0")

def gst_rate_for(transaction_date: date) -> Decimal:
    return GST_RATE if transaction_date >= GST_EFFECTIVE_DATE else NO_GST

def price_with_gst(amount: Decimal, transaction_date: date) -> Decimal:
    return (amount * (Decimal("1") + gst_rate_for(transaction_date))).quantize(Decimal("0.01"))
