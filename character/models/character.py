# from datetime import datetime
from datetime import timedelta
from celery import current_app
from decimal import Decimal
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.core.exceptions import ValidationError
from django.db import models, IntegrityError
from django.db.models import Sum
from django.utils import timezone
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, cast
import logging
import math

from users.models import Player

from gameplay.models import Currency, CurrencyAccountBase

from character.services import (
    character_services,
    lifecycle_services,
    link_services,
    relationship_services,
)
from locations.models import Movable, Node, Building
from progression.mixins import LevelProgressionMixin

logger = logging.getLogger("general")
logger_errors = logging.getLogger("errors")


########################################################################
####    RELATIONSHIPS & LIFECYCLE
########################################################################


class RelationshipType(models.TextChoices):
    FRIEND = "friend", "Friend"
    RIVAL = "rival", "Rival"
    MENTOR = "mentor", "Mentor"
    ENEMY = "enemy", "Enemy"
    ALLY = "ally", "Ally"
    ROMANTIC = "romantic", "Romantic"
    MARRIAGE = "marriage", "Marriage"
    PARENT_CHILD = "parent_child", "Parent/Child"
    SIBLING = "sibling", "Sibling"


class RelationshipRole(models.TextChoices):
    # Generic role for symmetric relationships, where members don't play
    # structurally different parts (friend, rival, romantic partner, ...).
    PARTICIPANT = "participant", "Participant"
    SPOUSE = "spouse", "Spouse"
    PARENT = "parent", "Parent"
    CHILD = "child", "Child"
    MENTOR = "mentor", "Mentor"
    MENTEE = "mentee", "Mentee"


@dataclass(frozen=True)
class RelationshipTypeSpec:
    """
    Structural rules for one relationship type: which roles it allows, how
    many members each role may have, and (for the roles-with-a-max-of-one
    kind of type) which `variant` values are meaningful.

    A role's `(min, max)` pair says how many members must/may hold it in a
    single relationship; `max=None` means unbounded. A type is directional
    exactly when it declares more than one distinct role - no separate flag
    needed, since that would just be state that could drift from `roles`.
    """

    roles: Dict[RelationshipRole, tuple]  # role -> (min, max | None)
    allowed_variants: frozenset = field(default_factory=frozenset)


# Symmetric relationships all reuse the same "any number of equal members"
# shape - defined once so `RELATIONSHIP_SPECS` doesn't repeat it per type.
_SYMMETRIC_GROUP = {RelationshipRole.PARTICIPANT: (2, None)}
_SYMMETRIC_PAIR = {RelationshipRole.PARTICIPANT: (2, 2)}

RELATIONSHIP_SPECS: Dict[RelationshipType, RelationshipTypeSpec] = {
    RelationshipType.FRIEND: RelationshipTypeSpec(roles=_SYMMETRIC_GROUP),
    RelationshipType.RIVAL: RelationshipTypeSpec(roles=_SYMMETRIC_GROUP),
    RelationshipType.ENEMY: RelationshipTypeSpec(roles=_SYMMETRIC_GROUP),
    RelationshipType.ALLY: RelationshipTypeSpec(roles=_SYMMETRIC_GROUP),
    RelationshipType.SIBLING: RelationshipTypeSpec(roles=_SYMMETRIC_GROUP),
    RelationshipType.ROMANTIC: RelationshipTypeSpec(roles=_SYMMETRIC_PAIR),
    RelationshipType.MARRIAGE: RelationshipTypeSpec(
        roles={RelationshipRole.SPOUSE: (2, 2)},
    ),
    RelationshipType.MENTOR: RelationshipTypeSpec(
        roles={
            RelationshipRole.MENTOR: (1, 1),
            RelationshipRole.MENTEE: (1, 1),
        },
    ),
    # Always binary: a child with two parents is two PARENT_CHILD
    # relationships, not one relationship with two PARENT members - keeps
    # every relationship's shape uniform (look up "the other role", never
    # "which parent").
    RelationshipType.PARENT_CHILD: RelationshipTypeSpec(
        roles={
            RelationshipRole.PARENT: (1, 1),
            RelationshipRole.CHILD: (1, 1),
        },
        allowed_variants=frozenset({"biological", "adoptive", "step", "foster"}),
    ),
}


class CharacterRelationship(models.Model):
    characters: models.ManyToManyField = models.ManyToManyField(
        "Character", through="CharacterRelationshipMembership"
    )

    relationship_type = models.CharField(
        max_length=20, choices=RelationshipType.choices
    )
    is_exclusive = models.BooleanField(default=False)
    strength = models.IntegerField(default=0)  # -100 (hatred) to 100 (deep bond)
    history = models.JSONField(default=dict, blank=True)  # Logs key events
    # Free-form but validated per relationship_type against
    # RELATIONSHIP_SPECS[type].allowed_variants (see clean()) - e.g.
    # "biological"/"adoptive"/"step"/"foster" for PARENT_CHILD. Blank means
    # unspecified. New variants are a RELATIONSHIP_SPECS edit, not a migration.
    variant = models.CharField(max_length=30, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def get_members(self):
        return [char for char in self.characters.all()]

    def is_romantic(self):
        return self.relationship_type == "romantic"

    def adjust_strength(self, amount):
        """Modify relationship strength."""
        return lifecycle_services.relationship_adjust_strength(self, amount)

    def log_event(self, event):
        """Add an event to the history log."""
        return lifecycle_services.relationship_log_event(self, event)

    def clean(self):
        super().clean()
        if not self.relationship_type:
            return
        try:
            spec = RELATIONSHIP_SPECS.get(RelationshipType(self.relationship_type))
        except ValueError:
            # Not a recognised type at all - clean_fields() already reported
            # this via the field's `choices`, nothing more to check here.
            return
        if spec is None:
            return
        if self.variant and self.variant not in spec.allowed_variants:
            raise ValidationError(
                {
                    "variant": (
                        f"'{self.variant}' is not a valid variant for "
                        f"{self.relationship_type} (allowed: "
                        f"{', '.join(sorted(spec.allowed_variants)) or 'none'})."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        characters_list = [str(char) for char in self.get_members()]
        return f"{self.relationship_type} between {', '.join(characters_list)}"


class CharacterRelationshipMembership(models.Model):
    character = models.ForeignKey(
        "Character",
        on_delete=models.CASCADE,
        related_name="characterrelationshipmembership",
    )
    relationship = models.ForeignKey("CharacterRelationship", on_delete=models.CASCADE)
    # null=True/blank=True kept from before choices were added, so this stays
    # a schema-metadata-only change - clean() (see below) is what actually
    # requires a valid role for relationship types that need one.
    role = models.CharField(
        max_length=20, choices=RelationshipRole.choices, null=True, blank=True
    )

    class Meta:
        unique_together = ("character", "relationship")

    def clean(self):
        super().clean()
        # Required FKs missing is already reported by clean_fields(); nothing
        # further to check against a relationship/character we don't have.
        if not self.relationship_id or not self.character_id:
            return

        try:
            spec = RELATIONSHIP_SPECS.get(
                RelationshipType(self.relationship.relationship_type)
            )
        except ValueError:
            return
        if spec is None:
            return

        if not self.role:
            raise ValidationError(
                {"role": "A role is required for this relationship type."}
            )

        try:
            role = RelationshipRole(self.role)
        except ValueError:
            # Not a recognised role at all - clean_fields() already reported
            # this via the field's `choices`, nothing more to check here.
            return

        if role not in spec.roles:
            allowed = ", ".join(sorted(r.value for r in spec.roles))
            raise ValidationError(
                {
                    "role": (
                        f"'{self.role}' is not a valid role for "
                        f"{self.relationship.relationship_type} (allowed: {allowed})."
                    )
                }
            )

        existing = CharacterRelationshipMembership.objects.filter(
            relationship_id=self.relationship_id
        ).exclude(pk=self.pk)

        if existing.filter(character_id=self.character_id).exists():
            raise ValidationError(
                "This character is already a member of this relationship."
            )

        _min, max_count = spec.roles[role]
        if max_count is not None:
            current_count = existing.filter(role=self.role).count()
            if current_count + 1 > max_count:
                raise ValidationError(
                    {
                        "role": (
                            f"{self.relationship.relationship_type} allows at most "
                            f"{max_count} member(s) with role '{self.role}'."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class LifeCycleMixin(models.Model):
    birth_date = models.DateField(null=True, blank=True)
    death_date = models.DateField(null=True, blank=True)
    cause_of_death = models.CharField(max_length=255, null=True, blank=True)
    fertility = models.PositiveIntegerField(default=50)
    last_childbirth_date = models.DateField(null=True, blank=True)
    is_pregnant = models.BooleanField(default=False)
    pregnancy_start_date = models.DateField(null=True, blank=True)
    pregnancy_due_date = models.DateField(null=True, blank=True)

    class Meta:
        abstract = True

    def get_age(self):
        return lifecycle_services.lifecycle_get_age(self)

    def die(self):
        return lifecycle_services.lifecycle_die(self)

    def is_alive(self):
        return lifecycle_services.lifecycle_is_alive(self)

    def get_romantic_partners(self):
        return lifecycle_services.lifecycle_get_romantic_partners(self)

    def is_fertile(self):
        return lifecycle_services.lifecycle_is_fertile(self)

    def can_reproduce_with(self, partner):
        return lifecycle_services.lifecycle_can_reproduce_with(self, partner)

    def attempt_pregnancy(self):
        return lifecycle_services.lifecycle_attempt_pregnancy(self)

    def start_pregnancy(self, partner):
        return lifecycle_services.lifecycle_start_pregnancy(self, partner)

    def handle_childbirth(self):
        return lifecycle_services.lifecycle_handle_childbirth(self)

    def handle_miscarriage(self):
        return lifecycle_services.lifecycle_handle_miscarriage(self)

    def get_miscarriage_change(self):
        return lifecycle_services.lifecycle_get_miscarriage_change(self)


########################################################################
####    CHARACTER MODEL
########################################################################


class CharacterQuerySet(models.QuerySet):
    def linkable(self):
        """
        Characters currently eligible to be linked to a player - the
        queryset-level equivalent of `Character.can_link`, for call sites
        that need to filter/exist-check in SQL rather than load instances.
        Keep this in sync with `Character.can_link` by hand; there's no
        way to share the logic verbatim since one runs in the DB and the
        other in Python.
        """
        cutoff_date = timezone.now().date() - timedelta(
            days=Character.MIN_LINK_AGE_DAYS
        )
        return (
            self.filter(is_reserved=False)
            .filter(
                models.Q(birth_date__isnull=True)
                | models.Q(birth_date__lte=cutoff_date)
            )
            .exclude(links__is_active=True)
        )


class CharacterManager(models.Manager.from_queryset(CharacterQuerySet)):
    pass


class Character(LevelProgressionMixin, LifeCycleMixin, Movable):
    class SexChoices(models.TextChoices):
        MALE = "Male", "Male"
        FEMALE = "Female", "Female"
        OTHER = "Other", "Other"

    xp = models.PositiveIntegerField(default=0)
    xp_next_level = models.PositiveIntegerField(default=100)
    xp_modifier = models.FloatField(default=1)
    level = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    given_name = models.CharField(max_length=50, default="")
    backstory = models.TextField(default="")
    population_centre = models.ForeignKey(
        "locations.PopulationCentre",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="residents",
    )

    sex = models.CharField(
        max_length=20, choices=SexChoices.choices, null=True, blank=True
    )
    reputation = models.IntegerField(default=0)
    is_reserved = models.BooleanField(
        default=False,
        verbose_name="Reserved",
        help_text="Manually held back from linking (e.g. reserved for a future storyline), independent of age or link status.",
    )
    link_points_multiplier = models.DecimalField(
        max_digits=5, decimal_places=2, default="1.00"
    )

    objects = CharacterManager()

    # Minimum age (in days) for a character to be linkable. ~18 years,
    # matching spawn-time character generation.
    MIN_LINK_AGE_DAYS = int(18 * 365.25)

    @property
    def is_npc(self):
        """
        A character is an NPC if they don't have an active PlayerCharacterLink.
        """
        return not self.links.filter(is_active=True).exists()

    @property
    def is_underage(self):
        # An unknown birth_date isn't evidence of being underage - it just
        # means age isn't gating linkability for this character.
        if self.birth_date is None:
            return False
        return self.get_age() < self.MIN_LINK_AGE_DAYS

    @property
    def can_link(self) -> bool:
        """
        Whether this character is currently eligible to be linked to a
        player, derived from independent reasons - manual reservation,
        age, active link, and (once population centres can gate linking -
        see #681) population_centre.characters_can_link - rather than a
        flag several call sites could clobber. Keep in sync by hand with
        `CharacterQuerySet.linkable`, the SQL-level equivalent used where
        a Python loop over instances isn't practical.
        """
        if self.is_reserved:
            return False
        if self.is_underage:
            return False
        if self.links.filter(is_active=True).exists():
            return False
        return True

    def __str__(self):
        return self.name

    @property
    def name(self):
        """
        Canonical display name - currently just given_name, but will later
        combine given_name with other components. Callers should read
        `.name`, never reconstruct it from `.given_name` themselves.
        """
        return self.given_name

    @property
    def total_activities(self):
        from progression.models import CharacterActivityArchive

        live_count = self.activities.filter(is_complete=True).count()
        archived_count = (
            CharacterActivityArchive.objects.filter(character=self).aggregate(
                total=Sum("record_count")
            )["total"]
            or 0
        )
        return live_count + archived_count

    @property
    def active_link(self):
        from character.models import PlayerCharacterLink

        return PlayerCharacterLink.objects.filter(
            character=self, is_active=True
        ).first()

    @property
    def current_player(self):
        """
        Retrieve the player associated with this character.
        """
        link = self.active_link
        return link.player if link else None

    @property
    def home(self):
        """The Building from this character's primary HOME CharacterLocation, if any."""
        from character.models.location import CharacterLocation

        home_location = self.locations.filter(
            role=CharacterLocation.Role.HOME, is_primary=True
        ).first()
        return home_location.location if home_location else None

    @property
    def parents(self):
        return relationship_services.relationship_get_parents(self)

    @property
    def children(self):
        return relationship_services.relationship_get_children(self)

    @property
    def siblings(self):
        return relationship_services.relationship_get_siblings(self)

    def relationships_of_type(self, relationship_type):
        return relationship_services.relationship_get_relationships_of_type(
            self, relationship_type
        )

    def add_parent(
        self, parent: "Character", variant: str = ""
    ) -> "CharacterRelationship":
        """Create a PARENT_CHILD relationship with `parent` as the parent, self as the child."""
        return relationship_services.relationship_create(
            RelationshipType.PARENT_CHILD,
            [(parent, RelationshipRole.PARENT), (self, RelationshipRole.CHILD)],
            variant=variant,
        )

    def get_currency(self, code="coins") -> "CharacterCurrency":
        currency_def, _ = Currency.objects.get_or_create(
            code=code,
            defaults={"name": code.replace("_", " ").title()},
        )
        currency, _ = self.currencies.get_or_create(currency=currency_def)
        return currency

    def react_to_sun_phase(self, phase):
        return character_services.character_react_to_sun_phase(self, phase)

    def assign_home(self, building: Building):
        return character_services.character_assign_home(self, building)

    def assign_work(self, building: Building):
        return character_services.character_assign_work(self, building)

    @classmethod
    def has_available(cls):
        return character_services.character_has_available(cls)

    @property
    def total_link_points(self):
        """
        Sum of link_points across every player link this character has ever
        had (past and current) - the character-side symmetric counterpart to
        Player.total_link_points.
        """
        return PlayerCharacterLink.total_link_points(self.links.all())

    def get_productivity(self, now=None):
        """
        Live productivity signal - see progression.ap.get_productivity for
        what drives it (authored baseline x current active XpModifiers).
        """
        from progression import ap

        return ap.get_productivity(self, now=now)


########################################################################
####    PLAYER CHARACTER LINK MODEL
########################################################################


class PlayerCharacterLink(models.Model):
    player = models.ForeignKey(
        "users.Player", on_delete=models.CASCADE, related_name="links"
    )
    character = models.ForeignKey(
        "Character", on_delete=models.CASCADE, related_name="links"
    )
    linked_at = models.DateTimeField(default=timezone.now)
    unlinked_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["player", "is_active"],
                condition=models.Q(is_active=True),
                name="one_active_link_per_player",
            ),
            models.UniqueConstraint(
                fields=["character", "is_active"],
                condition=models.Q(is_active=True),
                name="one_active_link_per_character",
            ),
        ]

    @property
    def days_linked(self):
        end_date = self.unlinked_at or timezone.now()
        return (end_date - self.linked_at).days

    @property
    def player_time(self):
        """
        Total completed activity time for this link (in seconds).
        """
        qs = self.player.activities.filter(
            is_complete=True, completed_at__gte=self.linked_at
        )

        if self.unlinked_at:
            qs = qs.filter(completed_at__lte=self.unlinked_at)

        total_seconds = qs.aggregate(total=Sum("duration"))["total"] or 0
        return int(total_seconds // 60)

    @property
    def link_points(self):
        total_days_points = self.days_linked * 20
        login_points = self.player.user.days_logged_in * 5
        time_points = (
            self.player_time // 10
        )  # 1 point for every 10 minutes of completed activities during the link period

        base_points = total_days_points + login_points + time_points
        multiplier = (
            self.player.link_points_multiplier * self.character.link_points_multiplier
        )
        return int(base_points * multiplier)

    @classmethod
    def get_character(cls, player: Player) -> Character:
        return link_services.player_link_get_character(cls, player)

    @classmethod
    def get_player(cls, character: Character) -> Player:
        return link_services.player_link_get_player(cls, character)

    def unlink(self):
        """Marks link as inactive and records unlink date"""
        return link_services.player_link_unlink(self)

    @classmethod
    def deactivate_active_links(cls, player: Player):
        return link_services.player_link_deactivate_active_links(cls, player)

    @classmethod
    def deactivate_active_links_for_character(cls, character: Character):
        return link_services.player_link_deactivate_active_links_for_character(
            cls, character
        )

    @classmethod
    def assign_character(cls, player: Player, character: Character):
        return link_services.player_link_assign_character(cls, player, character)

    @classmethod
    def total_link_points(cls, list_of_links):
        return sum(link.link_points for link in list_of_links)


class CharacterCurrency(CurrencyAccountBase):
    character = models.ForeignKey(
        Character,
        on_delete=models.CASCADE,
        related_name="currencies",
    )
    currency = models.ForeignKey(
        Currency,
        on_delete=models.CASCADE,
        related_name="character_accounts",
    )

    class Meta:
        unique_together = ("character", "currency")
