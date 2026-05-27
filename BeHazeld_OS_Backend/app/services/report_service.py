"""
ReportService — PDF invoice generation using ReportLab.

Public API
----------
generate_invoice_pdf(bill, tenant_name) → bytes
    Pure function: builds a professional invoice PDF in memory and returns
    the raw bytes. No file I/O — the caller decides where to persist it.

save_invoice_pdf(pdf_bytes, tenant_id, invoice_number) → InvoiceMetadata
    Saves bytes to INVOICE_STORAGE_PATH/{tenant_id}/{invoice_number}.pdf
    and returns InvoiceMetadata (path + file size).

Invoice layout
--------------
┌──────────────────────────────────────────────┐
│  [INVOICE]                    Business Name  │
│  Invoice: INV-000001          Date: 25-05-26 │
│  Customer: Walk-in                           │
├──────────────────────────────────────────────┤
│  # │ SKU   │ Description │ Qty │ Price │ Amt │
│  ─────────────────────────────────────────── │
│  1 │ ...   │ ...         │ 10  │ 200   │2000 │
├──────────────────────────────────────────────┤
│               Subtotal: ₹XXXX               │
│               Tax:      ₹XXXX               │
│               Discount: ₹XXXX               │
│               TOTAL:    ₹XXXX               │
├──────────────────────────────────────────────┤
│  Payment: Cash          Ref: TXN-001        │
└──────────────────────────────────────────────┘
"""
from __future__ import annotations

import io
import os
import uuid
from decimal import Decimal
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT

from app.core.config import settings
from app.schemas.sales import InvoiceMetadata

# ── Brand colours ─────────────────────────────────────────────────────────────
_PRIMARY   = colors.HexColor("#1A1A2E")   # deep navy
_ACCENT    = colors.HexColor("#E94560")   # coral-red
_LIGHT_BG  = colors.HexColor("#F5F5F5")
_WHITE     = colors.white
_GREY      = colors.HexColor("#666666")

# ── Page geometry ──────────────────────────────────────────────────────────────
_PAGE_W, _PAGE_H = A4
_MARGIN = 18 * mm


def generate_invoice_pdf(bill, tenant_name: str = "BeHazeld") -> bytes:
    """
    Build an invoice PDF from a SaleBill ORM object (or any object with the
    same attribute shape). Returns raw PDF bytes — no file I/O.

    Parameters
    ----------
    bill        : SaleBill ORM instance (or a MagicMock with matching attrs)
    tenant_name : Displayed as the business name in the header.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=_MARGIN,
        rightMargin=_MARGIN,
        topMargin=_MARGIN,
        bottomMargin=_MARGIN,
    )

    styles = getSampleStyleSheet()
    normal = styles["Normal"]

    h1 = ParagraphStyle("H1", fontSize=22, textColor=_PRIMARY,
                        spaceAfter=2, fontName="Helvetica-Bold")
    h2 = ParagraphStyle("H2", fontSize=10, textColor=_GREY,
                        fontName="Helvetica")
    label = ParagraphStyle("Label", fontSize=8, textColor=_GREY,
                           fontName="Helvetica")
    value = ParagraphStyle("Value", fontSize=10, textColor=_PRIMARY,
                           fontName="Helvetica-Bold")
    right_label = ParagraphStyle("RightLabel", fontSize=9, textColor=_GREY,
                                 fontName="Helvetica", alignment=TA_RIGHT)
    right_value = ParagraphStyle("RightValue", fontSize=11, textColor=_PRIMARY,
                                 fontName="Helvetica-Bold", alignment=TA_RIGHT)
    total_style = ParagraphStyle("TotalStyle", fontSize=13, textColor=_ACCENT,
                                 fontName="Helvetica-Bold", alignment=TA_RIGHT)

    story: list = []

    # ── Header ─────────────────────────────────────────────────────────────────
    header_data = [
        [
            Paragraph(f"<b>{tenant_name}</b>", h1),
            Paragraph("INVOICE", ParagraphStyle(
                "INV", fontSize=28, textColor=_ACCENT,
                fontName="Helvetica-Bold", alignment=TA_RIGHT,
            )),
        ]
    ]
    header_tbl = Table(header_data, colWidths=[(_PAGE_W - 2 * _MARGIN) * 0.6,
                                                (_PAGE_W - 2 * _MARGIN) * 0.4])
    header_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(header_tbl)
    story.append(HRFlowable(width="100%", thickness=2, color=_ACCENT, spaceAfter=6))

    # ── Invoice meta ───────────────────────────────────────────────────────────
    invoice_no = getattr(bill, "invoice_number", "—")
    bill_date  = getattr(bill, "bill_date", "—")
    customer   = getattr(bill, "customer", None)
    cust_name  = customer.name if customer else "Walk-in Customer"

    meta_data = [
        [
            Paragraph("<b>Invoice #</b>", label),
            Paragraph(str(invoice_no), value),
            "",
            Paragraph("<b>Date</b>", label),
            Paragraph(str(bill_date), value),
        ],
        [
            Paragraph("<b>Customer</b>", label),
            Paragraph(cust_name, value),
            "",
            Paragraph("<b>Status</b>", label),
            Paragraph(str(getattr(bill, "status", "confirmed")).upper(), value),
        ],
    ]
    usable_w = _PAGE_W - 2 * _MARGIN
    meta_tbl = Table(meta_data, colWidths=[
        usable_w * 0.15, usable_w * 0.30, usable_w * 0.05,
        usable_w * 0.15, usable_w * 0.35,
    ])
    meta_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(Spacer(1, 4 * mm))
    story.append(meta_tbl)
    story.append(Spacer(1, 4 * mm))

    # ── Line items table ───────────────────────────────────────────────────────
    col_headers = ["#", "SKU / Variant", "Qty", "Price", "Disc", "Tax%", "Amount"]
    tbl_data = [col_headers]

    lines = getattr(bill, "lines", []) or []
    for i, line in enumerate(lines, 1):
        variant_id = str(getattr(line, "product_variant_id", ""))[:8] + "…"
        qty        = getattr(line, "quantity", 0)
        price      = getattr(line, "selling_price", 0)
        disc       = getattr(line, "discount_amount", 0)
        tax_r      = float(getattr(line, "tax_rate", 0)) * 100
        total      = getattr(line, "total_line_amount", 0)
        tbl_data.append([
            str(i),
            variant_id,
            f"{qty:g}",
            f"₹{price:,.2f}",
            f"₹{disc:,.2f}",
            f"{tax_r:.0f}%",
            f"₹{total:,.2f}",
        ])

    col_ws = [
        usable_w * 0.05,
        usable_w * 0.30,
        usable_w * 0.08,
        usable_w * 0.14,
        usable_w * 0.10,
        usable_w * 0.09,
        usable_w * 0.14,
    ]
    items_tbl = Table(tbl_data, colWidths=col_ws, repeatRows=1)
    items_tbl.setStyle(TableStyle([
        # Header row
        ("BACKGROUND",  (0, 0), (-1, 0), _PRIMARY),
        ("TEXTCOLOR",   (0, 0), (-1, 0), _WHITE),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, 0), 8),
        ("ALIGN",       (0, 0), (-1, 0), "CENTER"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING",    (0, 0), (-1, 0), 6),
        # Data rows
        ("FONTNAME",   (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",   (0, 1), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_WHITE, _LIGHT_BG]),
        ("ALIGN",      (2, 1), (-1, -1), "RIGHT"),
        ("ALIGN",      (0, 1), (0, -1), "CENTER"),
        ("TOPPADDING",    (0, 1), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        # Grid
        ("LINEBELOW",  (0, 0), (-1, 0), 1, _PRIMARY),
        ("LINEBELOW",  (0, -1), (-1, -1), 0.5, _GREY),
    ]))
    story.append(items_tbl)
    story.append(Spacer(1, 4 * mm))

    # ── Totals ─────────────────────────────────────────────────────────────────
    gross       = getattr(bill, "total_amount", Decimal("0"))
    tax_amt     = getattr(bill, "tax_amount", Decimal("0"))
    disc_total  = getattr(bill, "total_discount", Decimal("0"))
    subtotal    = Decimal(str(gross)) + Decimal(str(disc_total)) - Decimal(str(tax_amt))

    def _row(lbl: str, val: str, bold: bool = False) -> list:
        s = total_style if bold else right_label
        return [
            "",
            Paragraph(lbl, right_label),
            Paragraph(val, total_style if bold else right_value),
        ]

    totals_data = [
        _row("Subtotal:", f"₹{subtotal:,.2f}"),
        _row("Tax:", f"₹{Decimal(str(tax_amt)):,.2f}"),
        _row("Discount:", f"-₹{Decimal(str(disc_total)):,.2f}"),
        _row("TOTAL DUE:", f"₹{Decimal(str(gross)):,.2f}", bold=True),
    ]
    totals_tbl = Table(totals_data, colWidths=[usable_w * 0.55, usable_w * 0.25, usable_w * 0.20])
    totals_tbl.setStyle(TableStyle([
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEABOVE", (1, -1), (-1, -1), 1.5, _ACCENT),
    ]))
    story.append(totals_tbl)
    story.append(Spacer(1, 4 * mm))

    # ── Payment info ───────────────────────────────────────────────────────────
    payments = getattr(bill, "payments", []) or []
    if payments:
        pay_rows = [["Payment Mode", "Amount", "Reference"]]
        for p in payments:
            pay_rows.append([
                str(getattr(p, "payment_mode", "")).replace("_", " ").title(),
                f"₹{getattr(p, 'amount', 0):,.2f}",
                str(getattr(p, "transaction_id", "") or "—"),
            ])
        pay_tbl = Table(pay_rows, colWidths=[usable_w * 0.35, usable_w * 0.25, usable_w * 0.40])
        pay_tbl.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, 0), _LIGHT_BG),
            ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",    (0, 0), (-1, -1), 8),
            ("ALIGN",       (1, 0), (1, -1), "RIGHT"),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LINEBELOW",   (0, 0), (-1, 0), 0.5, _GREY),
        ]))
        story.append(pay_tbl)

    story.append(Spacer(1, 6 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=_GREY))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(
        "Thank you for your purchase! This is a computer-generated invoice.",
        ParagraphStyle("Footer", fontSize=7, textColor=_GREY,
                       alignment=TA_CENTER, fontName="Helvetica-Oblique"),
    ))

    doc.build(story)
    return buf.getvalue()


def save_invoice_pdf(
    pdf_bytes: bytes,
    tenant_id: uuid.UUID,
    invoice_number: str,
) -> InvoiceMetadata:
    """
    Persist PDF bytes to local storage and return metadata.

    Path: {INVOICE_STORAGE_PATH}/{tenant_id}/{invoice_number}.pdf
    """
    base_dir = Path(settings.INVOICE_STORAGE_PATH) / str(tenant_id)
    base_dir.mkdir(parents=True, exist_ok=True)

    file_path = base_dir / f"{invoice_number}.pdf"
    file_path.write_bytes(pdf_bytes)

    return InvoiceMetadata(
        invoice_number=invoice_number,
        file_path=str(file_path),
        file_size_bytes=len(pdf_bytes),
    )
