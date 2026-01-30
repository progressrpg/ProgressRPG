from django.contrib.gis import admin

from .models import (
    Node,
    Path,
    InteriorSpace,
    Building,
    PopulationCentre,
    LandArea,
    Subzone,
)
from character.models import Character


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "kind")
    search_fields = ("name",)
    list_filter = ("kind",)


@admin.register(Path)
class PathAdmin(admin.ModelAdmin):
    list_display = ("from_node", "to_node", "length")
    list_filter = ("from_node", "to_node")
    autocomplete_fields = ("from_node", "to_node")


@admin.register(InteriorSpace)
class InteriorSpaceAdmin(admin.ModelAdmin):
    list_display = ["name", "id", "usage", "building"]
    list_filter = [
        "usage",
    ]
    readonly_fields = [
        "building",
    ]
    fields = [
        "name",
        "usage",
        "building",
    ]


class InteriorSpaceInline(admin.TabularInline):
    model = InteriorSpace
    extra = 0


class CharacterInline(admin.TabularInline):
    model = Character
    extra = 0


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    inlines = [InteriorSpaceInline, CharacterInline]
    list_display = [
        "name",
        "id",
        "building_type",
        "population_centre",
    ]
    list_filter = [
        "building_type",
        "population_centre",
    ]
    readonly_fields = [
        "building_type",
        "population_centre",
    ]
    fields = [
        "name",
        "description",
        "population_centre",
        "building_type",
    ]
    search_field = [
        "name",
    ]


class BuildingInline(admin.TabularInline):
    model = Building
    extra = 0


class LandAreaInline(admin.TabularInline):
    model = LandArea
    extra = 0


@admin.register(PopulationCentre)
class PopulationCentreAdmin(admin.ModelAdmin):
    inlines = [BuildingInline, LandAreaInline]
    search_field = ["name"]
    list_display = ["name", "building_count"]
    readonly_fields = ["building_count"]
    fields = [
        "name",
        "description",
        "building_count",
    ]

    def building_count(self, obj):
        return obj.buildings.count()

    building_count.short_description = "Buildings"


class SubzoneInline(admin.TabularInline):
    model = Subzone
    extra = 0


@admin.register(LandArea)
class LandAreaAdmin(admin.ModelAdmin):
    search_field = ["name"]
    inlines = [SubzoneInline]

    list_display = [
        "name",
        "size",
        "population_centre",
    ]
    list_filter = [
        "size",
        "population_centre",
    ]

    readonly_fields = [
        "population_centre",
    ]
    fields = [
        "name",
        "size",
        "population_centre",
    ]
