from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.shortcuts import render
from django.utils import timezone

from apps.payments.models import Invoice, Payment
from apps.payments.utils import (
    due_date_for, due_periods, monthly_collections, outstanding_totals,
    payment_summary_for_period,
)
from apps.properties.models import Building, Flat, Occupancy, Occupant


@login_required
def home(request):
    today = timezone.localdate()
    active_occs = Occupancy.objects.filter(end_date__isnull=True).select_related(
        "flat__building", "occupant")

    total_flats = Flat.objects.count()
    occupied = active_occs.count()
    vacant = total_flats - occupied
    occupancy_rate = round(occupied / total_flats * 100) if total_flats else 0

    # This month's rent collection
    summary = payment_summary_for_period(today.year, today.month, today)
    monthly_target = sum(float(o.rent_amount) for o in active_occs)
    received = float(
        Payment.objects.filter(
            status=Payment.Status.PAID, rent_year=today.year, rent_month=today.month
        ).aggregate(t=Sum("amount"))["t"] or 0
    )

    totals = outstanding_totals(today)

    # Recent payments
    recent_payments = (
        Payment.objects.select_related(
            "occupancy__occupant", "occupancy__flat__building", "invoice")
        .order_by("-created_at", "-id")[:6]
    )

    # Overdue & due-soon warnings
    overdue_rows, due_soon_rows = [], []
    for occ in active_occs:
        for d in due_periods(occ, today):
            row = {"occ": occ, **d}
            if d["status"] == Payment.Status.OVERDUE:
                overdue_rows.append(row)
            elif d["status"] == "due_soon":
                due_soon_rows.append(row)
    overdue_rows.sort(key=lambda r: r["days_overdue"], reverse=True)
    overdue_rows = overdue_rows[:8]

    # Upcoming 7 days
    upcoming = []
    week_end = today + timedelta(days=7)
    for occ in active_occs:
        due = due_date_for(today.year, today.month)
        if today <= due <= week_end:
            paid = occ.payments.filter(rent_year=today.year, rent_month=today.month).exists()
            if not paid:
                upcoming.append({"occ": occ, "due_date": due})
    upcoming.sort(key=lambda r: r["due_date"])

    # New occupants (last 30 days)
    new_occupants = Occupant.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=30)
    ).order_by("-created_at")[:5]

    collections = monthly_collections(6, today)

    context = {
        "page_title": "Dashboard",
        "section": "dashboard",
        "cards": {
            "total_occupants": Occupant.objects.count(),
            "occupied": occupied,
            "vacant": vacant,
            "total_flats": total_flats,
            "occupancy_rate": occupancy_rate,
            "monthly_target": monthly_target,
            "received": received,
            "collection_pct": round(received / monthly_target * 100) if monthly_target else 0,
            "outstanding": totals["outstanding"],
            "overdue_total": totals["overdue"],
            "buildings": Building.objects.count(),
        },
        "pie": {
            "paid": summary["paid"],
            "pending": summary["pending"],
            "overdue": summary["overdue"],
        },
        "collections": collections,
        "recent_payments": recent_payments,
        "overdue_rows": overdue_rows,
        "due_soon_rows": due_soon_rows[:5],
        "upcoming": upcoming,
        "new_occupants": new_occupants,
        "invoices_count": Invoice.objects.count(),
        "today": today,
    }
    return render(request, "dashboard/home.html", context)
