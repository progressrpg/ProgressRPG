from django.contrib.gis import admin
from economy.models import GoodsStock
from .models import (
    Node,
    Path,
    Road,
    InteriorSpace,
    Building,
    PopulationCentre,
    LandArea,
    Subzone,
)
from character.models import CharacterLocation


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


@admin.register(Road)
class RoadAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "width", "population_centre")
    list_filter = ("population_centre",)
    search_fields = ("name",)


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
    fields = ("name", "area_display")
    readonly_fields = ("name", "area_display")
    can_delete = False

    @admin.display(description="Area")
    def area_display(self, obj):
        rounded = round(obj.area, 1) if obj.area is not None else 0.0
        return f"{rounded} m²"

    def has_add_permission(self, request, obj=None):
        return False


class GoodsStockInline(admin.TabularInline):
    model = GoodsStock
    extra = 0
    can_delete = False

    fields = (
        "good_type",
        "quantity",
        "capacity",
    )
    readonly_fields = (
        "good_type",
        "capacity",
    )

    @admin.display(description="Capacity")
    def capacity(self, obj):
        return obj.capacity

    def has_add_permission(self, request, obj=None):
        return False


class CharacterInline(admin.TabularInline):
    model = CharacterLocation
    fk_name = "location"
    extra = 0
    fields = ("character",)
    readonly_fields = ("character",)
    can_delete = False
    show_change_link = True

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .filter(role=CharacterLocation.Role.HOME, is_primary=True)
        )

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    inlines = [InteriorSpaceInline, CharacterInline, GoodsStockInline]
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
        "description",
    ]
    fields = [
        "name",
        "description",
        "population_centre",
        "building_type",
        "open_time_override",
        "close_time_override",
    ]
    search_fields = [
        "name",
    ]


class BuildingInline(admin.TabularInline):
    model = Building
    extra = 0
    fields = ("building_type",)
    readonly_fields = ("building_type",)
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


class LandAreaInline(admin.TabularInline):
    model = LandArea
    extra = 0
    fields = ("name",)
    can_delete = False
    readonly_fields = ("name",)
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(PopulationCentre)
class PopulationCentreAdmin(admin.ModelAdmin):
    inlines = [BuildingInline, LandAreaInline]
    search_fields = ["name"]
    list_display = ["name", "building_count"]
    list_display_links = ["name"]
    readonly_fields = ["building_count"]
    fields = [
        "name",
        "description",
        "building_count",
    ]

    @admin.display(description="Buildings")
    def building_count(self, obj):
        return obj.buildings.count()


class SubzoneInline(admin.TabularInline):
    model = Subzone
    extra = 0
    can_delete = False
    fields = ("name", "area")
    readonly_fields = ("name", "area")

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description="Area (m²)")
    def area(self, obj):
        rounded = round(obj.size, 1) if obj.size is not None else 0.0
        return f"{rounded} m²"


@admin.register(LandArea)
class LandAreaAdmin(admin.ModelAdmin):
    search_fields = ["name"]
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
        "size_display",
    ]
    fields = [
        "name",
        "size_display",
        "population_centre",
    ]

    @admin.display(description="Area (hectares)")
    def size_display(self, obj):
        rounded = round(obj.size, 1) if obj.size is not None else 0.0
        return f"{rounded} ha"
