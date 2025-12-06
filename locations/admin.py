from django.contrib import admin

from .models import Building


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "name",
    ]
    readonly_fields = []
    fields = [
        "name",
        "description",
    ]
