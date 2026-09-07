from django.urls import path

from . import views

app_name = "properties"

urlpatterns = [
    path("", views.rental_overview, name="rental_overview"),
    path("buildings/", views.building_list, name="buildings"),
    path("buildings/<int:pk>/edit/", views.building_edit, name="building_edit"),
    path("units/add/", views.flat_create, name="flat_create"),
    path("units/<int:pk>/", views.flat_detail, name="flat_detail"),
    path("units/<int:pk>/edit/", views.flat_edit, name="flat_edit"),
    path("shops/<int:pk>/", views.shop_detail, name="shop_detail"),
    path("cottages/<int:pk>/", views.shop_detail, name="cottage_detail"),
    path("occupants/", views.occupant_list, name="occupants"),
    path("occupants/add/", views.occupant_create, name="occupant_create"),
    path("occupants/<int:pk>/", views.client_info, name="client_info"),
    path("occupants/<int:pk>/edit/", views.occupant_edit, name="occupant_edit"),
    path("occupancy/start/", views.occupancy_start, name="occupancy_start"),
    path("occupancy/<int:pk>/end/", views.occupancy_end, name="occupancy_end"),
    path("occupants/<int:occupant_id>/documents/upload/", views.document_upload,
         name="document_upload"),
    path("documents/<int:pk>/delete/", views.document_delete, name="document_delete"),
]
