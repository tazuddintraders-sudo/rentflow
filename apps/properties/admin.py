from django.contrib import admin

from .models import Building, Document, Flat, Level, Occupant, Occupancy


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ("building_no", "name", "total_flats", "occupied_flats")
    search_fields = ("building_no", "name")


@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ("building", "level_number", "name")
    list_filter = ("building",)


@admin.register(Flat)
class FlatAdmin(admin.ModelAdmin):
    list_display = ("building", "flat_no", "flat_type", "status", "current_rent")
    list_filter = ("building", "flat_type")
    search_fields = ("flat_no",)


@admin.register(Occupant)
class OccupantAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "nid_number", "current_flat")
    search_fields = ("name", "phone", "nid_number", "email")


@admin.register(Occupancy)
class OccupancyAdmin(admin.ModelAdmin):
    list_display = ("flat", "occupant", "start_date", "end_date", "rent_amount")
    list_filter = ("end_date",)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "document_type", "occupant", "upload_date")
    list_filter = ("document_type",)
