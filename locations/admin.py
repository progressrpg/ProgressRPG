from django.contrib import admin

from .models import Building


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "name",
        "position_display",
    ]
    readonly_fields = [
        "position",
    ]
    fields = [
        "name",
        "description",
        "position_display" "created_at",
        "updated_at",
    ]

    def position_display(self, obj):
        if obj.position:
            return f"({obj.position.x}, {obj.position.y})"
        return "No position"

    position_display.short_description = "Position"
