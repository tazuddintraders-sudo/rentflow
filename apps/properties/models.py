from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone


class Building(models.Model):
    building_no = models.CharField(max_length=20, unique=True, help_text="e.g. B-01")
    name = models.CharField(max_length=120)
    address = models.TextField(blank=True)
    photo = models.ImageField(upload_to="buildings/", blank=True, null=True)

    class Meta:
        ordering = ["building_no"]

    def __str__(self):
        return f"{self.building_no} — {self.name}"

    @property
    def total_flats(self):
        return self.flats.count()

    @property
    def occupied_flats(self):
        return self.flats.filter(occupancies__end_date__isnull=True).distinct().count()

    @property
    def vacant_flats(self):
        return self.total_flats - self.occupied_flats


class Level(models.Model):
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name="levels")
    level_number = models.PositiveIntegerField(help_text="0 = Ground floor")
    name = models.CharField(max_length=60, blank=True, help_text="e.g. Ground Floor")

    class Meta:
        ordering = ["building", "level_number"]
        unique_together = ("building", "level_number")

    def __str__(self):
        label = self.name or f"Level {self.level_number}"
        return f"{self.building.building_no} / {label}"


class Flat(models.Model):
    class FlatType(models.TextChoices):
        FLAT = "flat", "Flat"
        SHOP = "shop", "Shop"
        COTTAGE = "cottage", "Cottage"

    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name="flats")
    level = models.ForeignKey(
        Level, on_delete=models.SET_NULL, null=True, blank=True, related_name="flats"
    )
    flat_no = models.CharField(max_length=20)
    flat_type = models.CharField(max_length=10, choices=FlatType.choices, default=FlatType.FLAT)
    size_sqft = models.PositiveIntegerField(null=True, blank=True, verbose_name="Size (sqft)")
    amenities = models.TextField(blank=True, help_text="Comma separated, e.g. Lift, Generator, Parking")
    default_rent = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["building__building_no", "flat_no"]
        unique_together = ("building", "flat_no")

    def __str__(self):
        return f"{self.building.building_no} / {self.flat_no}"

    def get_absolute_url(self):
        return reverse("properties:flat_detail", args=[self.pk])

    @property
    def amenities_list(self):
        return [a.strip() for a in self.amenities.split(",") if a.strip()]

    @property
    def active_occupancy(self):
        return self.occupancies.filter(end_date__isnull=True).order_by("-start_date").first()

    @property
    def is_occupied(self):
        return self.occupancies.filter(end_date__isnull=True).exists()

    @property
    def status(self):
        return "Occupied" if self.is_occupied else "Vacant"

    @property
    def current_rent(self):
        occ = self.active_occupancy
        return occ.rent_amount if occ else self.default_rent


class Occupant(models.Model):
    class IDType(models.TextChoices):
        NID = "nid", "National ID (NID)"
        PASSPORT = "passport", "Passport"
        DRIVING = "driving", "Driving Licence"
        OTHER = "other", "Other ID"

    name = models.CharField(max_length=120)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20)
    alt_phone = models.CharField(max_length=20, blank=True, verbose_name="Alternate phone")
    id_type = models.CharField(max_length=12, choices=IDType.choices, default=IDType.NID)
    nid_number = models.CharField(max_length=40, blank=True, verbose_name="ID number")
    present_address = models.TextField(blank=True)
    permanent_address = models.TextField(blank=True)
    emergency_contact_name = models.CharField(max_length=120, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    photo = models.ImageField(upload_to="profiles/", blank=True, null=True)
    occupation = models.CharField(max_length=80, blank=True, help_text="e.g. Service, Business")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("properties:client_info", args=[self.pk])

    @property
    def active_occupancy(self):
        return self.occupancies.filter(end_date__isnull=True).order_by("-start_date").first()

    @property
    def current_flat(self):
        occ = self.active_occupancy
        return occ.flat if occ else None


class Occupancy(models.Model):
    flat = models.ForeignKey(Flat, on_delete=models.CASCADE, related_name="occupancies")
    occupant = models.ForeignKey(
        Occupant, on_delete=models.CASCADE, related_name="occupancies"
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    rent_amount = models.DecimalField(max_digits=10, decimal_places=2)
    advance_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    agreement_reference = models.CharField(max_length=80, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date"]
        verbose_name_plural = "Occupancies"

    def __str__(self):
        state = "active" if self.end_date is None else f"until {self.end_date}"
        return f"{self.occupant.name} @ {self.flat} ({state})"

    @property
    def is_active(self):
        return self.end_date is None

    def clean(self):
        if self.end_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": "End date cannot be before start date."})
        # Only one active occupancy per flat / per occupant.
        if self.end_date is None:
            qs = Occupancy.objects.filter(flat=self.flat, end_date__isnull=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError(
                    {"flat": "This flat already has an active occupancy. "
                             "End the existing one first."}
                )
            qs2 = Occupancy.objects.filter(occupant=self.occupant, end_date__isnull=True)
            if self.pk:
                qs2 = qs2.exclude(pk=self.pk)
            if qs2.exists():
                raise ValidationError(
                    {"occupant": "This occupant already has an active occupancy."}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


def document_upload_path(instance, filename):
    return f"documents/occupant_{instance.occupant_id}/{filename}"


class Document(models.Model):
    class DocType(models.TextChoices):
        NID = "nid", "NID / ID Card"
        AGREEMENT = "agreement", "Rental Agreement"
        LEGAL = "legal", "Legal Proof"
        PHOTO = "photo", "Photograph"
        OTHER = "other", "Other"

    occupant = models.ForeignKey(
        Occupant, on_delete=models.CASCADE, related_name="documents"
    )
    document_type = models.CharField(max_length=12, choices=DocType.choices)
    title = models.CharField(max_length=120)
    file = models.FileField(upload_to=document_upload_path)
    upload_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-upload_date"]

    def __str__(self):
        return f"{self.get_document_type_display()} — {self.occupant.name}"

    @property
    def extension(self):
        name = self.file.name.lower()
        if name.endswith(".pdf"):
            return "PDF"
        if any(name.endswith(e) for e in (".jpg", ".jpeg", ".png", ".webp")):
            return "IMG"
        return "FILE"
