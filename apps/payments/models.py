from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from apps.properties.models import Occupancy


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = "cash", "Cash"
        BANK = "bank", "Bank Transfer"
        BKASH = "bkash", "bKash"

    class Status(models.TextChoices):
        PAID = "paid", "Paid"
        PENDING = "pending", "Pending"
        OVERDUE = "overdue", "Overdue"

    occupancy = models.ForeignKey(
        Occupancy, on_delete=models.CASCADE, related_name="payments"
    )
    # The rental month this payment covers.
    rent_year = models.PositiveIntegerField()
    rent_month = models.PositiveSmallIntegerField()  # 1..12

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField(default=timezone.localdate)
    due_date = models.DateField()
    method = models.CharField(max_length=10, choices=Method.choices, default=Method.CASH)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PAID)

    # Method-specific details:
    #  cash  -> {"received_by": "...", "received_date": "..."}
    #  bank  -> {"sender_bank": "...", "receiver_bank": "...", "txn_ref": "...",
    #            "transfer_date": "...", "cheque_no": "..."}
    #  bkash -> {"txn_id": "...", "sender_number": "...", "txn_datetime": "...",
    #            "screenshot": "relative/path.jpg"}
    details = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="recorded_payments",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-payment_date", "-id"]
        unique_together = ("occupancy", "rent_year", "rent_month")

    def __str__(self):
        return f"{self.invoice_number_display} — {self.occupancy.occupant.name} — {self.amount}"

    def get_absolute_url(self):
        return reverse("payments:manage") + f"?highlight={self.pk}"

    @property
    def invoice_number_display(self):
        inv = getattr(self, "invoice", None)
        return inv.invoice_number if inv else f"PAY-{self.pk:05d}"

    @property
    def month_label(self):
        return timezone.datetime(self.rent_year, self.rent_month, 1).strftime("%B %Y")

    @property
    def occupant(self):
        return self.occupancy.occupant

    @property
    def flat(self):
        return self.occupancy.flat

    def days_overdue(self, today=None):
        today = today or timezone.localdate()
        if self.status == self.Status.OVERDUE:
            return (today - self.due_date).days
        return 0


def invoice_upload_path(instance, filename):
    return f"invoices/{instance.invoice_number}.pdf"


class Invoice(models.Model):
    payment = models.OneToOneField(
        Payment, on_delete=models.CASCADE, related_name="invoice"
    )
    invoice_number = models.CharField(max_length=24, unique=True, db_index=True)
    generated_date = models.DateTimeField(default=timezone.now)
    pdf = models.FileField(upload_to=invoice_upload_path, blank=True, null=True)
    emailed = models.BooleanField(default=False)
    emailed_to = models.EmailField(blank=True)
    emailed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-generated_date"]

    def __str__(self):
        return self.invoice_number
