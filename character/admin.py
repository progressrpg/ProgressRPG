from django.contrib import admin
from .models import (
    Character,
    PlayerCharacterLink,
    CharacterRelationship,
    Behaviour,
)

from django.contrib import messages


class LinkInline(admin.TabularInline):
    model = PlayerCharacterLink
    fields = ("player", "linked_at", "is_active")
    readonly_fields = ("linked_at",)
    extra = 0
    max_num = 1


class BehaviourInline(admin.StackedInline):
    model = Behaviour
    extra = 1
    max_num = 1


@admin.action(description="Mark selected characters as NPCs and unlink from players")
def mark_as_npc(modeladmin, request, queryset):
    for character in queryset:
        # Unlink any active PlayerCharacterLink
        active_links = character.links.filter(is_active=True)
        for link in active_links:
            link.unlink()

    messages.success(
        request, f"{queryset.count()} character(s) marked as NPC and unlinked."
    )


@admin.action(description="Mark selected characters as available to link")
def mark_as_canlink(modeladmin, request, queryset):
    for character in queryset:
        character.can_link = True
        character.save(update_fields=["can_link"])

    messages.success(
        request, f"{queryset.count()} character(s) marked as available to link."
    )


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            None,
            {
                "fields": (
                    ("first_name", "last_name"),
                    "can_link",
                    "sex",
                )
            },
        ),
        (
            "Location",
            {
                "fields": (
                    "current_node",
                    "building",
                    "population_centre",
                )
            },
        ),
        ("Dates", {"fields": (("birth_date", "death_date", "get_age"),)}),
        (
            "Life & Story",
            {
                "classes": ("collapse",),
                "fields": ("backstory", "parents", "cause_of_death"),
            },
        ),
        (
            "Stats",
            {
                "classes": ("collapse",),
                "fields": (
                    (
                        "coins",
                        "reputation",
                    )
                ),
            },
        ),
        (
            "Pregnancy Details",
            {
                "classes": ("collapse",),
                "fields": (
                    ("is_pregnant", "pregnancy_start_date", "pregnancy_due_date"),
                ),
            },
        ),
    )

    list_display = [
        "first_name",
        "last_name",
        "get_player",
        "can_link",
        "birth_date",
    ]
    list_filter = [
        "can_link",
        "birth_date",
        "death_date",
        "sex",
        "population_centre",
    ]
    search_fields = [
        "first_name",
        "last_name",
        "links__player__name",
    ]
    readonly_fields = [
        "get_player",
        "get_age",
        "parents",
        "created_at",
    ]

    ordering = ["last_name", "first_name"]
    inlines = [LinkInline, BehaviourInline]
    actions = [mark_as_npc, mark_as_canlink]

    @admin.display(description="Player")
    def get_player(self, obj):
        try:
            return PlayerCharacterLink.get_player(obj)
        except ValueError:
            return "-"

    @admin.display(description="Population Centre")
    def get_settlement(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html

        try:
            if obj.population_centre:
                url = reverse(
                    "admin:locations_populationcentre_change",
                    args=[obj.population_centre.id],
                )
                return format_html(
                    '<a href="{}">{}</a>', url, obj.population_centre.name
                )
                # return f"Settlement {obj.population_centre.name} (id: {obj.population_centre.id})"
            return "-"
        except AttributeError:
            return "-"

    @admin.display(boolean=True, description="Has Player")
    def has_player(self, obj):
        return PlayerCharacterLink.objects.filter(
            character=obj, is_active=True
        ).exists()

    @admin.display(description="Age")
    def get_age(self, obj):
        try:
            return f"{int(obj.get_age()/365)} years old"
        except Exception:
            return "-"


@admin.register(PlayerCharacterLink)
class PlayerCharacterLinkAdmin(admin.ModelAdmin):
    list_display = ["player", "character", "is_active", "linked_at", "unlinked_at"]
    fields = [
        ("player", "character", "is_active"),
        ("online_boost_active", "online_boost_ends_at"),
        ("linked_at", "unlinked_at"),
    ]
    readonly_fields = ["linked_at", "unlinked_at"]


class CharacterInline(admin.TabularInline):
    model = (
        CharacterRelationship.characters.through
    )  # Access the ManyToMany through model
    extra = 1


# @admin.register(CharacterRelationship)
class CharacterRelationshipAdmin(admin.ModelAdmin):
    list_display = [
        "relationship_type",
        "get_linked_characters",
        "last_updated",
    ]
    fields = [
        "relationship_type",
        "strength",
        "history",
        "biological",
        ("created_at", "last_updated"),
    ]
    inlines = [CharacterInline]
    readonly_fields = ["created_at", "last_updated"]

    @admin.display(description="Characters")
    def get_linked_characters(self, obj):
        return ", ".join([str(char) for char in obj.get_members()])
