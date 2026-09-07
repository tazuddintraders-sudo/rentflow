from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    BuildingForm, DocumentForm, EndOccupancyForm, FlatForm, OccupancyForm,
    OccupantForm,
)
from .models import Building, Document, Flat, Level, Occupant, Occupancy


# ---------------------------------------------------------------------------
# Rental overview (all units)
# ---------------------------------------------------------------------------
@login_required
def rental_overview(request):
    flats = (
        Flat.objects.select_related("building", "level")
        .prefetch_related("occupancies__occupant")
        .order_by("building__building_no", "flat_no")
    )
    buildings = Building.objects.all().order_by("building_no")

    building_id = request.GET.get("building", "")
    status = request.GET.get("status", "")
    ftype = request.GET.get("type", "")
    q = request.GET.get("q", "").strip()
    view = request.GET.get("view", "grid")

    if building_id:
        flats = flats.filter(building_id=building_id)
    if status == "occupied":
        flats = flats.filter(occupancies__end_date__isnull=True).distinct()
    elif status == "vacant":
        flats = flats.exclude(occupancies__end_date__isnull=True)
    if ftype:
        flats = flats.filter(flat_type=ftype)
    if q:
        flats = flats.filter(
            Q(flat_no__icontains=q)
            | Q(building__building_no__icontains=q)
            | Q(building__name__icontains=q)
            | Q(occupancies__occupant__name__icontains=q)
        ).distinct()

    # Payment light per occupied flat (paid / due soon / overdue this month).
    today = timezone.localdate()
    from apps.payments.utils import due_periods
    cards = []
    for flat in flats:
        occ = flat.active_occupancy
        state = "vacant"
        if occ:
            dues = due_periods(occ, today)
            if any(d["status"] == "overdue" for d in dues):
                state = "overdue"
            elif any(d["status"] == "due_soon" for d in dues):
                state = "due_soon"
            elif dues:
                state = "pending"
            else:
                state = "paid"
        cards.append({"flat": flat, "occ": occ, "state": state})

    context = {
        "page_title": "Rental Overview",
        "section": "properties",
        "cards": cards,
        "buildings": buildings,
        "total_flats": Flat.objects.count(),
        "occupied": sum(1 for c in cards if c["occ"]),
        "filters": {"building": building_id, "status": status, "type": ftype,
                    "q": q, "view": view},
        "flat_types": Flat.FlatType.choices,
    }
    return render(request, "properties/rental_overview.html", context)


# ---------------------------------------------------------------------------
# Buildings
# ---------------------------------------------------------------------------
@login_required
def building_list(request):
    if request.method == "POST":
        form = BuildingForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Building added.")
            return redirect("properties:buildings")
    else:
        form = BuildingForm()
    context = {
        "page_title": "Buildings",
        "section": "properties",
        "buildings": Building.objects.prefetch_related("flats", "levels").all(),
        "form": form,
    }
    return render(request, "properties/buildings.html", context)


@login_required
def building_edit(request, pk):
    building = get_object_or_404(Building, pk=pk)
    form = BuildingForm(request.POST or None, request.FILES or None, instance=building)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Building updated.")
        return redirect("properties:buildings")
    return render(request, "properties/form_page.html", {
        "page_title": f"Edit {building}", "form": form,
        "section": "properties", "cancel_url": "/properties/buildings/"})


# ---------------------------------------------------------------------------
# Flats / units
# ---------------------------------------------------------------------------
@login_required
def flat_create(request):
    form = FlatForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        flat = form.save()
        messages.success(request, f"Unit {flat.flat_no} added.")
        return redirect("properties:flat_detail", flat.pk)
    return render(request, "properties/form_page.html", {
        "page_title": "Add Unit", "form": form, "section": "properties",
        "cancel_url": "/properties/"})


@login_required
def flat_edit(request, pk):
    flat = get_object_or_404(Flat, pk=pk)
    form = FlatForm(request.POST or None, instance=flat)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Unit updated.")
        return redirect("properties:flat_detail", flat.pk)
    return render(request, "properties/form_page.html", {
        "page_title": f"Edit {flat}", "form": form, "section": "properties",
        "cancel_url": flat.get_absolute_url()})


@login_required
def flat_detail(request, pk):
    flat = get_object_or_404(
        Flat.objects.select_related("building", "level"), pk=pk)
    occ = flat.active_occupancy
    payment_history = []
    dues = []
    if occ:
        payment_history = list(
            occ.payments.select_related("invoice").order_by("-rent_year", "-rent_month")[:12]
        )
        from apps.payments.utils import due_periods
        dues = due_periods(occ)
    occupancy_form = OccupancyForm(initial={"flat": flat, "rent_amount": flat.default_rent})
    end_form = EndOccupancyForm(initial={"end_date": timezone.localdate()})
    doc_form = DocumentForm()
    context = {
        "page_title": f"{flat.get_flat_type_display()} {flat.flat_no}",
        "section": "properties",
        "flat": flat,
        "occ": occ,
        "payment_history": payment_history,
        "dues": dues,
        "occupancy_form": occupancy_form,
        "end_form": end_form,
        "doc_form": doc_form,
        "history_occupancies": flat.occupancies.select_related("occupant").order_by("-start_date"),
    }
    return render(request, "properties/flat_detail.html", context)


# Shop / cottage convenience routes (same data model)
@login_required
def shop_detail(request, pk):
    return flat_detail(request, pk)


# ---------------------------------------------------------------------------
# Occupants / clients
# ---------------------------------------------------------------------------
@login_required
def occupant_list(request):
    q = request.GET.get("q", "").strip()
    occupants = Occupant.objects.prefetch_related("occupancies").order_by("name")
    if q:
        occupants = occupants.filter(
            Q(name__icontains=q) | Q(phone__icontains=q) | Q(nid_number__icontains=q))
    return render(request, "properties/occupants.html", {
        "page_title": "Occupants", "section": "properties",
        "occupants": occupants, "q": q})


@login_required
def occupant_create(request):
    form = OccupantForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        person = form.save()
        messages.success(request, f"{person.name} added.")
        return redirect("properties:client_info", person.pk)
    return render(request, "properties/form_page.html", {
        "page_title": "Add Occupant", "form": form, "section": "properties",
        "cancel_url": "/properties/occupants/"})


@login_required
def occupant_edit(request, pk):
    person = get_object_or_404(Occupant, pk=pk)
    form = OccupantForm(request.POST or None, request.FILES or None, instance=person)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect("properties:client_info", person.pk)
    return render(request, "properties/form_page.html", {
        "page_title": f"Edit {person.name}", "form": form, "section": "properties",
        "cancel_url": person.get_absolute_url()})


@login_required
def client_info(request, pk):
    person = get_object_or_404(Occupant, pk=pk)
    occupancies = person.occupancies.select_related("flat__building", "flat__level")
    all_payments = []
    for occ in person.occupancies.all():
        all_payments.extend(list(occ.payments.select_related("occupancy__flat__building",
                                                             "invoice")))
    all_payments.sort(key=lambda p: (p.payment_date, p.id), reverse=True)
    context = {
        "page_title": person.name,
        "section": "properties",
        "person": person,
        "occupancies": occupancies,
        "payments": all_payments[:24],
        "documents": person.documents.all(),
        "doc_form": DocumentForm(),
    }
    return render(request, "properties/client_info.html", context)


# ---------------------------------------------------------------------------
# Occupancy actions
# ---------------------------------------------------------------------------
@login_required
@require_POST
def occupancy_start(request):
    form = OccupancyForm(request.POST)
    if form.is_valid():
        try:
            form.save()
            messages.success(request, "Occupancy started.")
        except Exception as exc:
            messages.error(request, f"Could not start occupancy: {exc}")
    else:
        messages.error(request, "; ".join(
            f"{k}: {v[0]}" for k, v in form.errors.items()))
    return redirect(request.META.get("HTTP_REFERER", "properties:rental_overview"))


@login_required
@require_POST
def occupancy_end(request, pk):
    occ = get_object_or_404(Occupancy, pk=pk)
    form = EndOccupancyForm(request.POST)
    if form.is_valid():
        occ.end_date = form.cleaned_data["end_date"]
        occ.save(update_fields=["end_date"])
        messages.success(request, f"Occupancy ended on {occ.end_date}.")
    else:
        messages.error(request, "Please provide a valid end date.")
    return redirect("properties:flat_detail", occ.flat_id)


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------
@login_required
@require_POST
def document_upload(request, occupant_id):
    person = get_object_or_404(Occupant, pk=occupant_id)
    form = DocumentForm(request.POST, request.FILES)
    if form.is_valid():
        doc = form.save(commit=False)
        doc.occupant = person
        doc.save()
        messages.success(request, f"“{doc.title}” uploaded.")
    else:
        messages.error(request, "; ".join(
            f"{k}: {v[0]}" for k, v in form.errors.items()))
    return redirect(request.META.get("HTTP_REFERER", person.get_absolute_url()))


@login_required
@require_POST
def document_delete(request, pk):
    doc = get_object_or_404(Document, pk=pk)
    target = doc.occupant.get_absolute_url()
    doc.delete()
    messages.success(request, "Document deleted.")
    return redirect(target)
