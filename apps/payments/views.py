import json
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q, Sum
from django.http import JsonResponse, HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from apps.properties.models import Building, Flat, Occupancy

from .models import Invoice, Payment
from .services import create_invoice_for_payment, render_invoice_pdf, send_invoices_email
from .utils import due_date_for, due_periods, month_label, outstanding_totals


# ---------------------------------------------------------------------------
# Landing page
# ---------------------------------------------------------------------------
@login_required
def payment_main(request):
    today = timezone.localdate()
    totals = outstanding_totals(today)
    pending = Payment.objects.filter(status=Payment.Status.PENDING).count()
    overdue_occs = []
    for occ in Occupancy.objects.filter(end_date__isnull=True).select_related("flat__building", "occupant"):
        dues = due_periods(occ, today)
        od = [d for d in dues if d["status"] == Payment.Status.OVERDUE]
        if od:
            overdue_occs.append({"occ": occ, "count": len(od),
                                 "amount": sum(d["rent"] for d in od),
                                 "oldest": od[0]})
    context = {
        "page_title": "Payments",
        "section": "payments",
        "outstanding": totals["outstanding"],
        "overdue_total": totals["overdue"],
        "pending_count": pending,
        "overdue_occs": overdue_occs[:6],
        "overdue_count": len(overdue_occs),
    }
    return render(request, "payments/payment_main.html", context)


# ---------------------------------------------------------------------------
# Payment portal (make payment / invoice generation)
# ---------------------------------------------------------------------------
@login_required
def make_payment(request):
    context = {
        "page_title": "Record Payment & Generate Invoice",
        "section": "payments",
        "buildings": Building.objects.all().order_by("building_no"),
        "today": timezone.localdate().isoformat(),
        "banks": [
            "City Bank Ltd.", "Dutch-Bangla Bank Ltd.", "BRAC Bank Ltd.",
            "Eastern Bank Ltd.", "Southeast Bank Ltd.", "Prime Bank Ltd.",
            "Islami Bank Bangladesh Ltd.", "Bank Asia Ltd.", "Other",
        ],
    }
    return render(request, "payments/make_payment.html", context)


@login_required
def flats_for_building(request, building_id):
    """AJAX: flats (with status) for the building dropdown."""
    flats = Flat.objects.filter(building_id=building_id).order_by("flat_no")
    return JsonResponse({
        "flats": [
            {"id": f.id, "flat_no": f.flat_no, "flat_type": f.get_flat_type_display(),
             "status": f.status}
            for f in flats
        ]
    })


@login_required
def flat_payment_info(request, flat_id):
    """AJAX: auto-fetched occupant + due-month data for the selected flat."""
    flat = get_object_or_404(Flat, pk=flat_id)
    occ = flat.active_occupancy
    if not occ:
        return JsonResponse({"occupied": False,
                             "message": "This unit is currently vacant."}, status=200)
    today = timezone.localdate()
    dues = due_periods(occ, today)
    return JsonResponse({
        "occupied": True,
        "occupancy_id": occ.id,
        "occupant": {
            "id": occ.occupant_id,
            "name": occ.occupant.name,
            "nid": occ.occupant.nid_number or "—",
            "id_type": occ.occupant.get_id_type_display(),
            "email": occ.occupant.email or "",
            "phone": occ.occupant.phone,
        },
        "flat": {"flat_no": flat.flat_no, "building": flat.building.building_no,
                 "building_name": flat.building.name},
        "rent": float(occ.rent_amount),
        "current_month": today.strftime("%B %Y"),
        "due_periods": dues,
    })


@login_required
@require_POST
def verify_payment(request):
    """AJAX: validate the submission before invoice generation."""
    data = json.loads(request.body or "{}")
    errors = []
    occ = None
    periods = data.get("periods") or []

    try:
        occ = Occupancy.objects.get(pk=data.get("occupancy_id"), end_date__isnull=True)
    except (Occupancy.DoesNotExist, TypeError, ValueError):
        errors.append("Please select a valid occupied unit.")

    if occ:
        paid = set(occ.payments.values_list("rent_year", "rent_month"))
        due = {(d["year"], d["month"]) for d in due_periods(occ)}
        selected = set()
        for p in periods:
            try:
                y, m = int(p["year"]), int(p["month"])
            except (KeyError, TypeError, ValueError):
                errors.append("One of the selected months is invalid.")
                continue
            selected.add((y, m))
            if (y, m) in paid:
                errors.append(f"{month_label(y, m)} is already paid.")
            elif (y, m) not in due:
                errors.append(f"{month_label(y, m)} is not a payable period for this lease.")
        if not selected:
            errors.append("Select at least one rent month to pay.")

        # Amount check
        try:
            amount = Decimal(str(data.get("amount", "0")))
        except InvalidOperation:
            amount = Decimal("0")
        expected = occ.rent_amount * len(selected) if selected else Decimal("0")
        if amount <= 0:
            errors.append("Enter the payment amount.")
        elif amount != expected:
            errors.append(
                f"Amount ৳{amount:,.2f} does not match the expected "
                f"৳{expected:,.2f} ({len(selected)} month(s) × ৳{occ.rent_amount:,.0f})."
            )

    method = data.get("method")
    details = data.get("details") or {}
    if method == Payment.Method.CASH:
        if not details.get("received_by"):
            errors.append("Cash: please enter who received the money.")
    elif method == Payment.Method.BANK:
        for field, label in [("txn_ref", "Transaction reference number"),
                             ("sender_bank", "your bank name")]:
            if not details.get(field):
                errors.append(f"Bank transfer: please enter {label}.")
    elif method == Payment.Method.BKASH:
        for field, label in [("txn_id", "bKash Transaction ID"),
                             ("sender_number", "sender's bKash number")]:
            if not details.get(field):
                errors.append(f"bKash: please enter the {label}.")
    else:
        errors.append("Choose a payment method.")

    if errors:
        return JsonResponse({"ok": False, "errors": errors})
    return JsonResponse({
        "ok": True,
        "message": "All checks passed — ready to generate the invoice.",
        "expected_amount": float(expected),
    })


@login_required
@require_POST
@transaction.atomic
def generate_invoice(request):
    """AJAX: create Payment(s) + Invoice PDF(s), optionally email them."""
    data = json.loads(request.body or "{}")
    result = {"ok": False, "errors": []}
    try:
        occ = Occupancy.objects.select_for_update().get(
            pk=data.get("occupancy_id"), end_date__isnull=True
        )
    except (Occupancy.DoesNotExist, TypeError, ValueError):
        return JsonResponse({"ok": False, "errors": ["Invalid occupancy."]}, status=400)

    periods = data.get("periods") or []
    method = data.get("method")
    details = data.get("details") or {}
    send_email = bool(data.get("send_email"))
    email_to = (data.get("email") or occ.occupant.email or "").strip()
    pay_date = parse_date(data.get("payment_date") or "") or timezone.localdate()

    # bKash screenshot (base64 data URL) -> save once under media/payments/bkash
    shot = data.get("screenshot_data")
    screenshot_path = None
    if shot and method == Payment.Method.BKASH and shot.startswith("data:") and "," in shot:
        import base64
        header, payload = shot.split(",", 1)
        ext = "png" if "png" in header.split(";")[0] else "jpg"
        from django.core.files.storage import default_storage
        screenshot_path = default_storage.save(
            f"payments/bkash/{occ.id}_{timezone.now():%Y%m%d%H%M%S}.{ext}",
            ContentFile(base64.b64decode(payload)),
        )
        details = {**details, "screenshot": screenshot_path}

    payments, invoices = [], []
    for p in sorted(periods, key=lambda x: (x["year"], x["month"])):
        y, m = int(p["year"]), int(p["month"])
        if occ.payments.filter(rent_year=y, rent_month=m).exists():
            result["errors"].append(f"{month_label(y, m)} is already paid.")
            continue
        pay = Payment.objects.create(
            occupancy=occ, rent_year=y, rent_month=m,
            amount=occ.rent_amount,
            payment_date=pay_date,
            due_date=due_date_for(y, m),
            method=method, status=Payment.Status.PAID,
            details=details, created_by=request.user,
        )
        invoice, _buf = create_invoice_for_payment(pay)
        payments.append(pay)
        invoices.append(invoice)

    if not payments:
        return JsonResponse(result, status=400)

    email_error = None
    if send_email and email_to:
        try:
            send_invoices_email(payments, invoices, email_to)
        except Exception as exc:  # SMTP misconfiguration must not lose the payment
            email_error = str(exc)

    return JsonResponse({
        "ok": True,
        "payments": [{"id": p.id, "month": month_label(p.rent_year, p.rent_month),
                      "amount": float(p.amount)} for p in payments],
        "invoices": [{"id": i.id, "number": i.invoice_number,
                      "pdf_url": f"/payments/invoice/{i.id}/pdf/"} for i in invoices],
        "emailed": send_email and not email_error,
        "email_error": email_error,
        "redirect": payments[0].get_absolute_url(),
    })


# ---------------------------------------------------------------------------
# Payment history / management
# ---------------------------------------------------------------------------
@login_required
def manage_payments(request):
    payments = (
        Payment.objects.select_related(
            "occupancy__occupant", "occupancy__flat__building", "invoice")
        .order_by("-payment_date", "-id")
    )
    q = request.GET.get("q", "").strip()
    building = request.GET.get("building", "")
    status = request.GET.get("status", "")
    method = request.GET.get("method", "")
    date_from = request.GET.get("from", "")
    date_to = request.GET.get("to", "")

    if q:
        payments = payments.filter(
            Q(occupancy__occupant__name__icontains=q)
            | Q(occupancy__flat__flat_no__icontains=q)
            | Q(occupancy__flat__building__building_no__icontains=q)
            | Q(occupancy__occupant__nid_number__icontains=q)
            | Q(invoice__invoice_number__icontains=q)
        )
    if building:
        payments = payments.filter(occupancy__flat__building_id=building)
    if status:
        payments = payments.filter(status=status)
    if method:
        payments = payments.filter(method=method)
    if date_from:
        payments = payments.filter(payment_date__gte=date_from)
    if date_to:
        payments = payments.filter(payment_date__lte=date_to)

    payments = list(payments)
    total_amount = sum((p.amount for p in payments), Decimal("0"))
    paid_amount = sum((p.amount for p in payments if p.status == Payment.Status.PAID),
                      Decimal("0"))
    avg = (total_amount / len(payments)) if payments else Decimal("0")

    context = {
        "page_title": "Payment History",
        "section": "payments",
        "payments": payments,
        "buildings": Building.objects.all().order_by("building_no"),
        "statuses": Payment.Status.choices,
        "methods": Payment.Method.choices,
        "filters": {"q": q, "building": building, "status": status, "method": method,
                    "from": date_from, "to": date_to},
        "total_amount": total_amount,
        "paid_amount": paid_amount,
        "count": len(payments),
        "avg": avg,
    }
    return render(request, "payments/manage_payments.html", context)


@login_required
def payment_detail(request, pk):
    """AJAX: full details for the right-hand slide-over panel."""
    p = get_object_or_404(
        Payment.objects.select_related(
            "occupancy__occupant", "occupancy__flat__building", "occupancy__flat__level",
            "invoice", "created_by"),
        pk=pk,
    )
    try:
        invoice = p.invoice
    except Invoice.DoesNotExist:
        invoice = None
    screenshot_url = None
    if p.details.get("screenshot"):
        screenshot_url = p.details["screenshot"]
        if not screenshot_url.startswith("/"):
            screenshot_url = "/media/" + screenshot_url
    return JsonResponse({
        "id": p.id,
        "invoice_number": invoice.invoice_number if invoice else f"PAY-{p.pk:05d}",
        "month": p.month_label,
        "amount": float(p.amount),
        "payment_date": p.payment_date.strftime("%d %b %Y"),
        "due_date": p.due_date.strftime("%d %b %Y"),
        "status": p.status,
        "status_display": p.get_status_display(),
        "method": p.method,
        "method_display": p.get_method_display(),
        "details": p.details,
        "screenshot_url": screenshot_url,
        "occupant": {
            "name": p.occupant.name, "phone": p.occupant.phone,
            "email": p.occupant.email, "nid": p.occupant.nid_number,
            "url": p.occupant.get_absolute_url(),
        },
        "flat": str(p.flat),
        "flat_url": p.flat.get_absolute_url(),
        "has_invoice": invoice is not None,
        "pdf_url": f"/payments/invoice/{invoice.pk}/pdf/" if invoice else None,
        "resend_url": f"/payments/invoice/{invoice.pk}/resend/" if invoice else None,
        "invoice_id": invoice.pk if invoice else None,
        "emailed": invoice.emailed if invoice else False,
        "emailed_to": invoice.emailed_to if invoice else "",
        "recorded_by": (p.created_by.get_full_name() or p.created_by.username)
                       if p.created_by else "—",
    })


@login_required
@require_POST
def payment_status(request, pk):
    """AJAX: edit payment status (Paid/Pending/Overdue)."""
    p = get_object_or_404(Payment, pk=pk)
    new_status = json.loads(request.body or "{}").get("status")
    if new_status in dict(Payment.Status.choices):
        p.status = new_status
        p.save(update_fields=["status"])
        return JsonResponse({"ok": True, "status": new_status})
    return JsonResponse({"ok": False, "error": "Invalid status."}, status=400)


@login_required
@require_POST
def payment_delete(request, pk):
    p = get_object_or_404(Payment, pk=pk)
    p.delete()
    messages.success(request, "Payment record deleted.")
    return JsonResponse({"ok": True})


# ---------------------------------------------------------------------------
# Invoices
# ---------------------------------------------------------------------------
def _invoice_pdf_response(invoice, download=True):
    if invoice.pdf and invoice.pdf.name:
        fh = invoice.pdf.open("rb")
        data = fh.read()
        fh.close()
    else:
        data = render_invoice_pdf(invoice, invoice.payment).read()
    resp = HttpResponse(data, content_type="application/pdf")
    disp = "attachment" if download else "inline"
    resp["Content-Disposition"] = f"{disp}; filename={invoice.invoice_number}.pdf"
    return resp


@login_required
def invoice_pdf(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    return _invoice_pdf_response(invoice, download=True)


@login_required
def invoice_preview(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    return _invoice_pdf_response(invoice, download=False)


@login_required
@require_POST
def invoice_resend(request, pk):
    invoice = get_object_or_404(Invoice.objects.select_related("payment__occupancy"), pk=pk)
    email = (json.loads(request.body or "{}").get("email")
             or invoice.payment.occupant.email).strip()
    if not email:
        return JsonResponse({"ok": False, "error": "No email address available."}, status=400)
    try:
        send_invoices_email([invoice.payment], [invoice], email)
    except Exception as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)
    return JsonResponse({"ok": True, "email": email})
