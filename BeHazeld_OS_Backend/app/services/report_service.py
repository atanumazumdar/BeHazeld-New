"""Generate branded BeHazel'd sale invoices from the approved PDF template."""
from __future__ import annotations

import io
import uuid
from decimal import Decimal
from pathlib import Path
from textwrap import shorten

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

from app.core.config import settings
from app.schemas.sales import InvoiceMetadata


_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "assets" / "invoice-template.pdf"
TEMPLATE_VERSION = "behazeld-gst-canva-v3-aligned"
_PAGE_WIDTH, _PAGE_HEIGHT = 810.0, 1012.5
_ITEMS_PER_PAGE = 15


def _money(value: object) -> str:
    return f"Rs. {Decimal(str(value or 0)):,.2f}"


def _quantity(value: object) -> str:
    quantity = Decimal(str(value or 0))
    return format(quantity.normalize(), "f")


def _line_description(line: object) -> str:
    variant = getattr(line, "variant", None)
    product = getattr(variant, "product", None)
    product_name = getattr(product, "name", None) or "Product"
    sku = getattr(variant, "sku_code", None)
    description = f"{product_name} - {sku}" if sku else product_name
    return shorten(str(description), width=46, placeholder="...")


def _overlay_page(
    bill: object,
    lines: list[object],
    page_number: int,
    page_count: int,
    show_totals: bool,
) -> bytes:
    stream = io.BytesIO()
    pdf = canvas.Canvas(stream, pagesize=(_PAGE_WIDTH, _PAGE_HEIGHT))
    pdf.setFillColorRGB(0.08, 0.08, 0.08)

    customer = getattr(bill, "customer", None)
    customer_name = getattr(customer, "name", None) or "Walk-in Customer"
    customer_phone = getattr(customer, "phone", None) or "-"
    bill_date = getattr(bill, "bill_date", "-")
    invoice_number = getattr(bill, "invoice_number", "-")

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(194, 836, shorten(str(customer_name), width=32, placeholder="..."))
    pdf.drawString(194, 792, shorten(str(customer_phone), width=28, placeholder="..."))
    pdf.drawString(630, 836, shorten(str(invoice_number), width=18, placeholder="..."))
    pdf.drawString(630, 792, str(bill_date))

    pdf.setFont("Helvetica", 10)
    start_index = page_number * _ITEMS_PER_PAGE
    row_y = 714
    for row_index, line in enumerate(lines):
        serial = start_index + row_index + 1
        quantity = getattr(line, "quantity", 0)
        price = getattr(line, "selling_price", 0)
        total = getattr(line, "total_line_amount", 0)

        pdf.drawCentredString(47, row_y, str(serial))
        pdf.drawString(150, row_y, _line_description(line))
        pdf.drawRightString(438, row_y, _quantity(quantity))
        pdf.drawRightString(582, row_y, _money(price))
        pdf.drawRightString(697, row_y, _money(total))
        row_y -= 28

    if page_count > 1:
        pdf.setFont("Helvetica", 8)
        pdf.drawCentredString(_PAGE_WIDTH / 2, 304, f"Page {page_number + 1} of {page_count}")

    if show_totals:
        gross = Decimal(str(getattr(bill, "total_amount", 0) or 0))
        discount = Decimal(str(getattr(bill, "total_discount", 0) or 0))
        tax = Decimal(str(getattr(bill, "tax_amount", 0) or 0))
        subtotal = gross + discount - tax

        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawRightString(766, 184, _money(subtotal))
        pdf.drawRightString(766, 144, _money(discount))
        pdf.drawRightString(766, 104, _money(gross))

    pdf.save()
    return stream.getvalue()


def generate_invoice_pdf(bill: object, tenant_name: str = "BeHazeld") -> bytes:
    """Overlay live sale data onto the approved BeHazel'd invoice template."""
    if not _TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Invoice template not found: {_TEMPLATE_PATH}")

    lines = list(getattr(bill, "lines", []) or [])
    page_count = max(1, (len(lines) + _ITEMS_PER_PAGE - 1) // _ITEMS_PER_PAGE)
    template_page = PdfReader(str(_TEMPLATE_PATH)).pages[0]
    writer = PdfWriter()

    for page_number in range(page_count):
        first = page_number * _ITEMS_PER_PAGE
        page_lines = lines[first:first + _ITEMS_PER_PAGE]
        page = PdfReader(io.BytesIO(_overlay_page(
            bill,
            page_lines,
            page_number,
            page_count,
            show_totals=page_number == page_count - 1,
        ))).pages[0]
        page.merge_page(template_page, over=False)
        writer.add_page(page)

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def save_invoice_pdf(
    pdf_bytes: bytes,
    tenant_id: uuid.UUID,
    invoice_number: str,
) -> InvoiceMetadata:
    base_dir = Path(settings.INVOICE_STORAGE_PATH) / str(tenant_id)
    base_dir.mkdir(parents=True, exist_ok=True)
    file_path = base_dir / f"{invoice_number}.pdf"
    file_path.write_bytes(pdf_bytes)
    file_path.with_suffix(".pdf.template-version").write_text(
        TEMPLATE_VERSION,
        encoding="ascii",
    )
    return InvoiceMetadata(
        invoice_number=invoice_number,
        file_path=str(file_path),
        file_size_bytes=len(pdf_bytes),
    )
