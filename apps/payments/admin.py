from django.contrib import admin

from .models import Invoice, Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "occupancy", "rent_year", "rent_month", "amount",
                    "payment_date", "method", "status")
    list_filter = ("status", "method", "rent_year", "rent_month")
    search_fields = ("occupancy__occupant__name", "occupancy__flat__flat_no",
                     "invoice__invoice_number")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "payment", "generated_date", "emailed", "emailed_to")
    search_fields = ("invoice_number",)
