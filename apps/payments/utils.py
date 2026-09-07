"""
Rent-flow calculation helpers.

A rent *period* is a calendar month (year, month), 1 = January.
Rent for month M is due on RENTFLOW["RENT_DUE_DAY"] of month M.
"""

from calendar import monthrange
from datetime import date

from django.conf import settings
from django.db.models import Sum
from django.utils import timezone

from .models import Invoice, Payment


DUE_DAY = lambda: int(settings.RENTFLOW["RENT_DUE_DAY"])  # noqa: E731

MONTH_NAMES = ["", "January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December"]


def month_label(year, month):
    return f"{MONTH_NAMES[month]} {year}"


def shift_month(year, month, delta):
    """Return (year, month) shifted by `delta` months (can be negative)."""
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


def months_between(start, end):
    """Inclusive list of (year, month) tuples from start to end."""
    out = []
    y, m = start
    end_index = end[0] * 12 + end[1]
    while y * 12 + m <= end_index:
        out.append((y, m))
        y, m = shift_month(y, m, 1)
    return out


def due_date_for(year, month):
    day = DUE_DAY()
    last_day = monthrange(year, month)[1]
    return date(year, month, min(day, last_day))


def period_status(year, month, today=None):
    """Paid/Pending/Overdue classification for a rent period."""
    today = today or timezone.localdate()
    due = due_date_for(year, month)
    if today > due:
        return Payment.Status.OVERDUE
    if due >= today:
        # Still inside or before the due month.
        return Payment.Status.PENDING
    return Payment.Status.PAID


def paid_periods(occupancy):
    """Set of (year, month) already paid for an occupancy."""
    return set(
        occupancy.payments.values_list("rent_year", "rent_month")
    )


def due_periods(occupancy, today=None):
    """
    All unpaid periods from the occupancy start month up to the current month,
    each annotated with status (overdue / pending / due-soon).
    Returns list of dicts.
    """
    today = today or timezone.localdate()
    if occupancy.start_date > today:
        return []
    start = (occupancy.start_date.year, occupancy.start_date.month)
    current = (today.year, today.month)
    paid = paid_periods(occupancy)
    out = []
    for (y, m) in months_between(start, current):
        if (y, m) in paid:
            continue
        due = due_date_for(y, m)
        days = (today - due).days
        if days > 0:
            status = Payment.Status.OVERDUE
        elif days >= -3:
            status = "due_soon"  # due within 3 days
        else:
            status = Payment.Status.PENDING
        out.append({
            "year": y, "month": m,
            "label": month_label(y, m),
            "due_date": due.isoformat(),
            "days_overdue": max(days, 0),
            "status": status,
            "rent": float(occupancy.rent_amount),
        })
    # Oldest first (oldest overdue at top is most urgent) — keep that order.
    return out


def next_invoice_number(now=None):
    """INV-YYYY-MM-XXXX, XXXX = sequence within the calendar month."""
    now = now or timezone.localtime()
    prefix = f"INV-{now.year:04d}-{now.month:02d}-"
    count = Invoice.objects.filter(invoice_number__startswith=prefix).count()
    return f"{prefix}{count + 1:04d}"


def payment_summary_for_period(year, month, today=None):
    """Used by the dashboard: how many active occupancies paid / pending / overdue."""
    today = today or timezone.localdate()
    active = Occupancy_active_qs()
    total = active.count()
    paid_ids = set(
        Payment.objects.filter(rent_year=year, rent_month=month, status=Payment.Status.PAID)
        .values_list("occupancy_id", flat=True)
    )
    paid = sum(1 for o in active if o.id in paid_ids)
    due = due_date_for(year, month)
    overdue = total - paid if today > due else 0
    pending = total - paid - overdue
    return {"total": total, "paid": paid, "pending": pending, "overdue": max(overdue, 0)}


def Occupancy_active_qs():
    from apps.properties.models import Occupancy
    return Occupancy.objects.filter(end_date__isnull=True).select_related("flat", "occupant")


def monthly_collections(months_back=6, today=None):
    """List of {label, amount} for the last N months, oldest first."""
    today = today or timezone.localdate()
    out = []
    y, m = today.year, today.month
    start_y, start_m = shift_month(y, m, -(months_back - 1))
    paid = {
        (p["rent_year"], p["rent_month"]): p["total"]
        for p in (
            Payment.objects.filter(status=Payment.Status.PAID)
            .values("rent_year", "rent_month")
            .annotate(total=Sum("amount"))
        )
    }
    for (yy, mm) in months_between((start_y, start_m), (y, m)):
        out.append({
            "label": MONTH_NAMES[mm][:3],
            "year": yy, "month": mm,
            "amount": float(paid.get((yy, mm), 0) or 0),
        })
    return out


def outstanding_totals(today=None):
    """Outstanding amount across active occupancies (sum of unpaid due rent)."""
    today = today or timezone.localdate()
    total = 0.0
    overdue = 0.0
    occupancies = Occupancy_active_qs()
    for occ in occupancies:
        dues = due_periods(occ, today)
        for d in dues:
            total += d["rent"]
            if d["status"] == Payment.Status.OVERDUE:
                overdue += d["rent"]
    return {"outstanding": total, "overdue": overdue}
