from django.contrib.gis import admin

from .models import Building, PopulationCentre


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


class BuildingInline(admin.TabularInline):
    model = Building
    extra = 0


@admin.register(PopulationCentre)
class PopulationCentreAdmin(admin.ModelAdmin):
    search_field = ["name"]

    inlines = [BuildingInline]
    list_display = ["name", "building_count"]
    readonly_fields = []
    fields = [
        "name",
        "description",
    ]

    def building_count(self, obj):
        return obj.buildings.count()

    building_count.short_description = "Buildings"
