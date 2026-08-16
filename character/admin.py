from typing import Dict

from django.contrib import admin
from .models import (
    Character,
    CharacterCurrency,
    CharacterLocation,
    PlayerCharacterLink,
    CharacterRelationship,
    CharacterRelationshipMembership,
    Behaviour,
    RELATIONSHIP_SPECS,
    RelationshipRole,
    RelationshipType,
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


class CharacterCurrencyInline(admin.TabularInline):
    model = CharacterCurrency
    extra = 0
    fields = ("currency", "earned", "spent", "balance", "last_calculated_at")
    readonly_fields = ("balance",)


class CharacterRelationshipMembershipInline(admin.TabularInline):
    model = CharacterRelationshipMembership
    fk_name = "character"
    extra = 0
    fields = ("get_relationship_type", "relationship", "role", "get_other_members")
    readonly_fields = ("get_relationship_type", "get_other_members")
    ordering = ("relationship__relationship_type",)

    @admin.display(description="Type")
    def get_relationship_type(self, obj):
        if not obj.pk:
            return "-"
        return obj.relationship.get_relationship_type_display()

    @admin.display(description="With")
    def get_other_members(self, obj):
        if not obj.pk:
            return "-"
        others = obj.relationship.characters.exclude(pk=obj.character_id)
        return ", ".join(str(c) for c in others)


class CanLinkListFilter(admin.SimpleListFilter):
    """
    can_link is a derived property, not a DB column, so it can't be listed
    in list_filter directly - filter via Character.objects.linkable()
    (the queryset-level equivalent) instead.
    """

    title = "can link"
    parameter_name = "can_link"

    def lookups(self, request, model_admin):
        return (("yes", "Yes"), ("no", "No"))

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(pk__in=Character.objects.linkable())
        if self.value() == "no":
            return queryset.exclude(pk__in=Character.objects.linkable())
        return queryset


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


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "given_name",
                    "can_link",
                    "is_reserved",
                    "sex",
                )
            },
        ),
        (
            "Location",
            {
                "fields": (
                    "current_node",
                    "population_centre",
                )
            },
        ),
        ("Dates", {"fields": (("birth_date", "death_date", "get_age"),)}),
        (
            "Family",
            {
                "fields": ("get_family_summary",),
            },
        ),
        (
            "Life & Story",
            {
                "classes": ("collapse",),
                "fields": ("backstory", "cause_of_death"),
            },
        ),
        (
            "Stats",
            {
                "classes": ("collapse",),
                "fields": (("reputation",)),
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
        "name",
        "get_player",
        "can_link",
        "birth_date",
    ]
    list_filter = [
        CanLinkListFilter,
        "is_reserved",
        "birth_date",
        "death_date",
        "sex",
        "population_centre",
    ]
    search_fields = [
        "given_name",
        "links__player__name",
    ]
    readonly_fields = [
        "can_link",
        "get_player",
        "get_age",
        "created_at",
        "get_family_summary",
    ]

    ordering = ["given_name"]
    inlines = [
        LinkInline,
        CharacterRelationshipMembershipInline,
        CharacterCurrencyInline,
    ]
    actions = [mark_as_npc]

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

    @admin.display(description="Family")
    def get_family_summary(self, obj):
        if not obj.pk:
            return "-"

        def names(characters):
            return ", ".join(str(c) for c in characters) or "-"

        parts = [
            f"Parents: {names(obj.parents)}",
            f"Children: {names(obj.children)}",
            f"Siblings: {names(obj.siblings)}",
        ]
        return " · ".join(parts)


@admin.register(PlayerCharacterLink)
class PlayerCharacterLinkAdmin(admin.ModelAdmin):
    list_display = ["player", "character", "is_active", "linked_at", "unlinked_at"]
    fields = [
        ("player", "character", "is_active"),
        ("linked_at", "unlinked_at"),
    ]
    readonly_fields = ["linked_at", "unlinked_at"]


@admin.register(CharacterLocation)
class CharacterLocationAdmin(admin.ModelAdmin):
    list_display = ["character", "role", "location", "is_primary"]
    list_filter = ["role", "is_primary"]
    search_fields = ["character__given_name", "location__name"]


@admin.register(CharacterCurrency)
class CharacterCurrencyAdmin(admin.ModelAdmin):
    list_display = ["character", "currency", "balance", "earned", "spent"]
    list_filter = ["currency"]
    search_fields = [
        "character__given_name",
        "currency__code",
        "currency__name",
    ]
    readonly_fields = ["balance"]


class CharacterInline(admin.TabularInline):
    model = (
        CharacterRelationship.characters.through
    )  # Access the ManyToMany through model
    extra = 1


@admin.register(CharacterRelationship)
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
        "variant",
        ("created_at", "last_updated"),
    ]
    inlines = [CharacterInline]
    readonly_fields = ["created_at", "last_updated"]

    @admin.display(description="Characters")
    def get_linked_characters(self, obj):
        return ", ".join([str(char) for char in obj.get_members()])

    def save_related(self, request, form, formsets, change):
        # Membership inlines save one row at a time, so a relationship can
        # be left transiently incomplete (e.g. a PARENT_CHILD relationship
        # with only its PARENT role filled in) - that's allowed (see
        # CharacterRelationshipMembership.clean()), but warn staff here
        # rather than silently leaving it incomplete.
        super().save_related(request, form, formsets, change)
        relationship = form.instance
        spec = RELATIONSHIP_SPECS.get(RelationshipType(relationship.relationship_type))
        if spec is None:
            return

        counts: Dict[RelationshipRole, int] = {}
        for membership in relationship.characterrelationshipmembership_set.all():
            if not membership.role:
                continue
            role = RelationshipRole(membership.role)
            counts[role] = counts.get(role, 0) + 1

        missing = [
            role.value
            for role, (min_count, _max_count) in spec.roles.items()
            if counts.get(role, 0) < min_count
        ]
        if missing:
            messages.warning(
                request,
                f"This {relationship.relationship_type} relationship is missing "
                f"required role(s): {', '.join(missing)}.",
            )
