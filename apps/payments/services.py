"""
Invoice generation (ReportLab) + email delivery.

ReportLab is pure-Python and packages cleanly with PyInstaller, which makes it
the best PDF choice for the Windows desktop build (WeasyPrint would require a
GTK runtime on every user's machine).

One invoice is generated per Payment record (a rent period). When several
months are paid in one go, several invoices are produced and attached to a
single email.
"""

import io
from decimal import Decimal

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

from .models import Invoice, Payment
from .utils import month_label, next_invoice_number

# ---------------------------------------------------------------------------
# Brand palette (kept in sync with static/css/variables.css)
# ---------------------------------------------------------------------------
NAVY = (0.055, 0.145, 0.277)       # #0E2547
ORANGE = (0.910, 0.490, 0.196)     # #E87D32
INK = (0.133, 0.165, 0.212)        # #222A36
GRAY = (0.435, 0.475, 0.541)       # #6F798A
LINE = (0.886, 0.902, 0.925)       # #E2E6EC
BG_SOFT = (0.965, 0.973, 0.984)    # #F6F8FB

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _styles():
    ss = getSampleStyleSheet()
    return {
        "company": ParagraphStyle("company", parent=ss["Normal"], fontName="Helvetica-Bold",
                                  fontSize=15, textColor=colors.Color(*NAVY), leading=18),
        "address": ParagraphStyle("address", parent=ss["Normal"], fontName="Helvetica",
                                  fontSize=8, textColor=colors.Color(*GRAY), leading=11),
        "h1": ParagraphStyle("h1", parent=ss["Normal"], fontName="Helvetica-Bold",
                             fontSize=24, textColor=colors.Color(*NAVY), leading=28,
                             alignment=2),
        "invno": ParagraphStyle("invno", parent=ss["Normal"], fontName="Helvetica-Bold",
                                fontSize=9.5, textColor=colors.Color(*ORANGE), alignment=2,
                                leading=14),
        "label": ParagraphStyle("label", parent=ss["Normal"], fontName="Helvetica",
                                fontSize=7.5, textColor=colors.Color(*GRAY), leading=10),
        "value": ParagraphStyle("value", parent=ss["Normal"], fontName="Helvetica-Bold",
                                fontSize=9, textColor=colors.Color(*INK), leading=13),
        "th": ParagraphStyle("th", parent=ss["Normal"], fontName="Helvetica-Bold",
                             fontSize=8, textColor=colors.white, leading=11),
        "td": ParagraphStyle("td", parent=ss["Normal"], fontName="Helvetica",
                             fontSize=9, textColor=colors.Color(*INK), leading=12),
        "tdb": ParagraphStyle("tdb", parent=ss["Normal"], fontName="Helvetica-Bold",
                              fontSize=9, textColor=colors.Color(*INK), leading=12),
        "note": ParagraphStyle("note", parent=ss["Normal"], fontName="Helvetica",
                               fontSize=8, textColor=colors.Color(*GRAY), leading=12),
        "paybox": ParagraphStyle("paybox", parent=ss["Normal"], fontName="Helvetica",
                                 fontSize=8.5, textColor=colors.Color(*INK), leading=14),
    }


def _money(value):
    return f"\u09f3 {Decimal(value):,.2f}"


def render_invoice_pdf(invoice, payment):
    """Build an invoice PDF for a single payment into a BytesIO buffer."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
        title=f"Invoice {invoice.invoice_number}",
    )
    s = _styles()
    story = []
    R = settings.RENTFLOW
    occupant = payment.occupant
    flat = payment.flat
    right_align = ParagraphStyle("ra", parent=s["tdb"], alignment=2)
    white_bold = ParagraphStyle("wb", parent=s["tdb"], textColor=colors.white)
    white_bold_r = ParagraphStyle("wbr", parent=s["tdb"], textColor=colors.white,
                                  alignment=2, fontSize=11)

    # --- Header -----------------------------------------------------------
    header = Table(
        [[
            Paragraph(R["COMPANY_NAME"].upper(), s["company"]),
            Paragraph("INVOICE", s["h1"]),
        ],
        [
            Paragraph(f"{R['ADDRESS']}<br/>{R['PHONE']} &nbsp;&middot;&nbsp; {R['EMAIL']}",
                      s["address"]),
            Paragraph(f"{invoice.invoice_number}<br/>"
                      f"Issued {timezone.localdate().strftime('%d %b %Y')}", s["invno"]),
        ]],
        colWidths=[100 * mm, 74 * mm],
    )
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 1), (-1, 1), 1.4, colors.Color(*NAVY)),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(header)
    story.append(Spacer(1, 10 * mm))

    # --- Bill-to / property / lease ---------------------------------------
    def block(label, lines):
        inner = [[Paragraph(label.upper(), s["label"])]]
        for ln in lines:
            inner.append([Paragraph(ln, s["value"])])
        t = Table(inner, colWidths=[58 * mm])
        t.setStyle(TableStyle([
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
        ]))
        return t

    billed = block("Billed to", [
        occupant.name,
        f"{occupant.get_id_type_display()}: {occupant.nid_number or '—'}",
        occupant.phone,
        occupant.email or "—",
    ])
    prop = block("Property", [
        f"Building {flat.building.building_no} — {flat.building.name}",
        f"{flat.get_flat_type_display()} {flat.flat_no}"
        + (f", Level {flat.level.level_number}" if flat.level else ""),
        flat.building.address or "",
    ])
    meta = block("Lease", [
        f"Started {payment.occupancy.start_date.strftime('%d %b %Y')}",
        f"Rent {_money(payment.occupancy.rent_amount)} / month",
        f"Paid on {payment.payment_date.strftime('%d %b %Y')}",
    ])
    info = Table([[billed, prop, meta]], colWidths=[58 * mm, 60 * mm, 56 * mm])
    info.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(info)
    story.append(Spacer(1, 8 * mm))

    # --- Line items --------------------------------------------------------
    head = [
        Paragraph("RENT PERIOD", s["th"]),
        Paragraph("DESCRIPTION", s["th"]),
        Paragraph("DUE DATE", s["th"]),
        Paragraph("PAID VIA", s["th"]),
        Paragraph("AMOUNT", ParagraphStyle("thr", parent=s["th"], alignment=2)),
    ]
    rows = [head, [
        Paragraph(month_label(payment.rent_year, payment.rent_month), s["tdb"]),
        Paragraph(f"Rent for {flat.flat_no}, Building {flat.building.building_no}", s["td"]),
        Paragraph(payment.due_date.strftime("%d %b %Y"), s["td"]),
        Paragraph(payment.get_method_display(), s["td"]),
        Paragraph(_money(payment.amount), right_align),
    ], [
        Paragraph("TOTAL PAID", white_bold), "", "", "",
        Paragraph(_money(payment.amount), white_bold_r),
    ]]
    table = Table(rows, colWidths=[34 * mm, 60 * mm, 26 * mm, 26 * mm, 28 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(*NAVY)),
        ("BACKGROUND", (0, 1), (-1, 1), colors.Color(*BG_SOFT)),
        ("BACKGROUND", (0, -1), (-1, -1), colors.Color(*ORANGE)),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.Color(*NAVY)),
        ("LINEABOVE", (0, -1), (-1, -1), 1.2, colors.Color(*NAVY)),
        ("GRID", (0, 1), (-1, 1), 0.4, colors.Color(*LINE)),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(table)
    story.append(Spacer(1, 8 * mm))

    # --- Method details + payment instructions -----------------------------
    d = payment.details or {}
    detail_lines = [f"<b>Recorded via {payment.get_method_display()}.</b>"]
    if payment.method == Payment.Method.CASH:
        detail_lines += [
            f"Received by: {d.get('received_by', '—')}",
            f"Received on: {d.get('received_date', '—')}",
        ]
    elif payment.method == Payment.Method.BANK:
        detail_lines += [
            f"Sender bank: {d.get('sender_bank', '—')}",
            f"Receiver bank: {d.get('receiver_bank') or R['BANK_NAME']}",
            f"Transaction ref: {d.get('txn_ref', '—')}",
            f"Cheque no: {d.get('cheque_no') or '—'}",
        ]
    elif payment.method == Payment.Method.BKASH:
        detail_lines += [
            f"bKash transaction ID: {d.get('txn_id', '—')}",
            f"Sender number: {d.get('sender_number', '—')}",
        ]

    pay_box = Table([[
        Paragraph("<br/>".join(detail_lines), s["paybox"]),
        Paragraph(
            f"<b>Payment instructions</b><br/>"
            f"Bank: {R['BANK_NAME']}<br/>"
            f"A/C: {R['BANK_ACCOUNT']}<br/>"
            f"Routing: {R['BANK_ROUTING']}<br/>"
            f"bKash: {R['BKASH_NUMBER']}",
            s["paybox"],
        ),
    ]], colWidths=[90 * mm, 84 * mm])
    pay_box.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, colors.Color(*LINE)),
        ("BACKGROUND", (0, 0), (-1, -1), colors.Color(*BG_SOFT)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(pay_box)
    story.append(Spacer(1, 10 * mm))

    story.append(Paragraph(
        "This is a computer-generated invoice and is valid without signature. "
        "Please quote the invoice number with any correspondence. "
        f"Thank you for renting with {R['COMPANY_SHORT']}.",
        s["note"],
    ))

    doc.build(story)
    buf.seek(0)
    return buf


def create_invoice_for_payment(payment, save=True):
    """Create an Invoice (with PDF) for one payment. Returns (invoice, buffer)."""
    invoice = Invoice(payment=payment, invoice_number=next_invoice_number())
    if save:
        invoice.save()
        buf = render_invoice_pdf(invoice, payment)
        invoice.pdf.save(f"{invoice.invoice_number}.pdf",
                         ContentFile(buf.read()), save=True)
    else:
        buf = render_invoice_pdf(invoice, payment)
    return invoice, buf


def send_invoices_email(payments, invoices, to_email):
    """Send one email to the occupant with every generated invoice attached."""
    R = settings.RENTFLOW
    occupant = payments[0].occupant
    total = sum((p.amount for p in payments), Decimal("0"))
    months = ", ".join(month_label(p.rent_year, p.rent_month) for p in payments)
    invoice_numbers = ", ".join(i.invoice_number for i in invoices)

    html = f"""
    <div style="font-family:Arial,Helvetica,sans-serif;color:#222A36;max-width:560px">
      <div style="background:#0E2547;padding:22px 28px;border-radius:10px 10px 0 0">
        <span style="color:#ffffff;font-size:18px;font-weight:bold">{R['COMPANY_SHORT']}</span>
        <span style="color:#E87D32;font-size:18px;font-weight:bold">.</span>
      </div>
      <div style="border:1px solid #E2E6EC;border-top:0;padding:26px 28px;border-radius:0 0 10px 10px">
        <h2 style="margin:0 0 6px;color:#0E2547">Rent receipt</h2>
        <p style="margin:0 0 18px;color:#6F798A;font-size:14px">Invoice(s): {invoice_numbers}</p>
        <p style="font-size:14px;line-height:1.6">Dear <b>{occupant.name}</b>,</p>
        <p style="font-size:14px;line-height:1.6">
          Thank you — your rent payment for <b>{months}</b> has been received and recorded.
          Your invoice(s) are attached to this email as PDF.
        </p>
        <table style="width:100%;border-collapse:collapse;font-size:14px;margin:8px 0 18px">
          <tr><td style="padding:7px 0;color:#6F798A">Total paid</td>
              <td style="padding:7px 0;text-align:right;font-weight:bold">\u09f3 {total:,.2f}</td></tr>
          <tr><td style="padding:7px 0;color:#6F798A">Property</td>
              <td style="padding:7px 0;text-align:right">{payments[0].flat}</td></tr>
          <tr><td style="padding:7px 0;color:#6F798A">Payment date</td>
              <td style="padding:7px 0;text-align:right">{payments[0].payment_date:%d %b %Y}</td></tr>
        </table>
        <p style="font-size:13px;color:#6F798A;line-height:1.6">
          Please keep this receipt for your records. If you have any questions,
          reply to this email or call {R['PHONE']}.
        </p>
        <p style="font-size:14px">Warm regards,<br/><b>{R['COMPANY_NAME']}</b></p>
      </div>
    </div>
    """
    msg = EmailMultiAlternatives(
        subject=f"Your RentFlow invoice(s) — {months}",
        body=(
            f"Dear {occupant.name},\n\n"
            f"Your rent payment for {months} has been received.\n"
            f"Amount: \u09f3 {total:,.2f}\nProperty: {payments[0].flat}\n"
            f"Invoices: {invoice_numbers} (attached as PDF).\n\n"
            f"Thank you,\n{R['COMPANY_NAME']}"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email],
    )
    msg.attach_alternative(html, "text/html")
    for inv in invoices:
        if inv.pdf:
            msg.attach(f"{inv.invoice_number}.pdf", inv.pdf.read(), "application/pdf")
    msg.send()

    now = timezone.now()
    for inv in invoices:
        inv.emailed = True
        inv.emailed_to = to_email
        inv.emailed_at = now
        inv.save(update_fields=["emailed", "emailed_to", "emailed_at"])
