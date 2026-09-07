from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("", views.payment_main, name="main"),
    path("make/", views.make_payment, name="make_payment"),
    path("api/building/<int:building_id>/flats/", views.flats_for_building,
         name="api_flats"),
    path("api/flat/<int:flat_id>/info/", views.flat_payment_info, name="api_flat_info"),
    path("api/verify/", views.verify_payment, name="api_verify"),
    path("api/generate/", views.generate_invoice, name="api_generate"),
    path("history/", views.manage_payments, name="manage"),
    path("api/payment/<int:pk>/", views.payment_detail, name="api_detail"),
    path("api/payment/<int:pk>/status/", views.payment_status, name="api_status"),
    path("api/payment/<int:pk>/delete/", views.payment_delete, name="api_delete"),
    path("invoice/<int:pk>/pdf/", views.invoice_pdf, name="invoice_pdf"),
    path("invoice/<int:pk>/preview/", views.invoice_preview, name="invoice_preview"),
    path("invoice/<int:pk>/resend/", views.invoice_resend, name="invoice_resend"),
]
