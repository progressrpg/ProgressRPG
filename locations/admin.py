from django.contrib.gis import admin

from .models import InteriorSpace, Building, PopulationCentre, LandArea, Subzone
from character.models import Character

@admin.register(InteriorSpace)
class InteriorSpaceAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "id",
        "usage",
        "building"
    ]
    list_filter = [
        "area",
        "usage",
    ]
    readonly_fields = [
        "building",
    ]
    fields = [
        "id",
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
    search_field = ["name"]

    inlines = [BuildingInline, LandAreaInline]
    list_display = ["name", "building_count"]
    readonly_fields = []
    fields = [
        "name",
        "description",
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
    ]
    
    readonly_fields = [
        "population_centre",
    ]
    fields = [
        "name",
        "size",
        "population_centre",
    ]

