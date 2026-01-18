from django.contrib import admin
from .models import (
    Character,
    PlayerCharacterLink,
    CharacterRelationship,
    CharacterRole,
    CharacterProgression,
    Behaviour,
)

from django.contrib import messages


class LinkInline(admin.TabularInline):
    model = PlayerCharacterLink
    extra = 0


class BehaviourInline(admin.StackedInline):
    model = Behaviour
    extra = 1
    max_num = 1


@admin.action(description="Mark selected characters as NPCs and unlink from profiles")
def mark_as_npc(modeladmin, request, queryset):
    for character in queryset:
        # Unlink any active PlayerCharacterLink
        active_links = character.profile_link.filter(is_active=True)
        for link in active_links:
            link.unlink()

        # Mark character as NPC
        character.is_npc = True
        character.save(update_fields=["is_npc"])

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
                    ("is_npc", "can_link"),
                    "sex",
                )
            },
        ),
        ("Dates", {"fields": (("birth_date", "death_date"))}),
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
        "get_profile",
        "is_npc",
        "can_link",
        "birth_date",
        "death_date",
    ]
    list_filter = [
        "is_npc",
        "can_link",
        "birth_date",
        "death_date",
        "sex",
    ]
    search_fields = [
        "first_name",
        "last_name",
        "profile_link__profile__name",
    ]
    readonly_fields = [
        "get_profile",
    ]
    ordering = ["last_name", "first_name"]
    inlines = [LinkInline, BehaviourInline]
    actions = [mark_as_npc, mark_as_canlink]

    @admin.display(description="Profile")
    def get_profile(self, obj):
        try:
            return PlayerCharacterLink.get_profile(obj)
        except ValueError:
            return "-"

    @admin.display(boolean=True, description="Has Profile")
    def has_profile(self, obj):
        return PlayerCharacterLink.objects.filter(
            character=obj, is_active=True
        ).exists()


@admin.register(PlayerCharacterLink)
class PlayerCharacterLinkAdmin(admin.ModelAdmin):
    list_display = ["profile", "character", "is_active"]
    fields = ["profile", "character", "is_active", ("date_linked", "date_unlinked")]
    readonly_fields = ["date_linked", "date_unlinked"]


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


# @admin.register(CharacterRole)
class CharacterRoleAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "description",
    ]


# @admin.register(CharacterProgression)
class CharacterProgressionAdmin(admin.ModelAdmin):
    list_display = [
        "character",
        "role",
    ]
    fields = [
        "character",
        "role",
        "experience",
        "date_started",
        "base_progression_rate",
        "player_acceleration_factor",
    ]
