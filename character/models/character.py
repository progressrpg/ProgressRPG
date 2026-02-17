# from datetime import datetime
from celery import current_app
from decimal import Decimal
from django.db import models, transaction, IntegrityError
from django.db.models import Sum
from django.utils import timezone
from random import random, randint
from typing import TYPE_CHECKING, Optional, Dict, Any, cast
import logging
import math
import random

from users.models import Person, Player

from gameplay.models import QuestCompletion, Quest
from gameplay.serializers import QuestResultSerializer
from progression.models import CharacterQuest
from progress_rpg.exceptions import QuestError

from character.services import character_services, lifecycle_services, link_services

if TYPE_CHECKING:
    from gameplay.models import QuestTimer

logger = logging.getLogger("general")
logger_errors = logging.getLogger("errors")


########################################################################
####    RELATIONSHIPS & LIFECYCLE
########################################################################


class CharacterRelationship(models.Model):
    characters = models.ManyToManyField(
        "Character", through="CharacterRelationshipMembership"
    )

    RELATIONSHIP_TYPES = [
        ("friend", "Friend"),
        ("rival", "Rival"),
        ("mentor", "Mentor"),
        ("enemy", "Enemy"),
        ("ally", "Ally"),
        ("romantic", "Romantic"),
        ("spouse", "Spouse"),
        ("parent", "Parent"),
        ("child", "Child"),
        ("sibling", "Sibling"),
    ]
    relationship_type = models.CharField(max_length=20, choices=RELATIONSHIP_TYPES)
    is_exclusive = models.BooleanField(default=False)
    strength = models.IntegerField(default=0)  # -100 (hatred) to 100 (deep bond)
    history = models.JSONField(default=dict, blank=True)  # Logs key events
    biological = models.BooleanField(
        default=True
    )  # True = blood relative, False = adopted/found family
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
    role = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        unique_together = ("character", "relationship")


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


class Character(Person, LifeCycleMixin, Movable):
    quest_completions = models.ManyToManyField(
        "gameplay.Quest",
        through="gameplay.QuestCompletion",
        related_name="completed_by",
    )

    class SexChoices(models.TextChoices):
        MALE = "Male", "Male"
        FEMALE = "Female", "Female"
        OTHER = "Other", "Other"

    first_name = models.CharField(max_length=50, default="")
    last_name = models.CharField(max_length=50, default="", null=True, blank=True)
    backstory = models.TextField(default="")
    
    parents = models.ManyToManyField(
        "self", related_name="children", symmetrical=False, blank=True
    )
    sex = models.CharField(
        max_length=20, choices=SexChoices.choices, null=True, blank=True
    )
    coins = models.PositiveIntegerField(default=0)
    reputation = models.IntegerField(default=0)
    can_link = models.BooleanField(default=False)

    @property
    def is_npc(self):
        """
        A character is an NPC if they don't have an active PlayerCharacterLink.
        """
        return not self.links.filter(is_active=True).exists()

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def total_quests(self):
        return (
            QuestCompletion.objects.filter(character=self).aggregate(
                total=Sum("times_completed")
            )["total"]
            or 0
        )

    @property
    def total_activities(self):
        return self.activities.filter(is_complete=True).count()

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

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
        return PlayerCharacterLink.get_player(self)

    def react_to_sun_phase(self, phase):
        return character_services.character_react_to_sun_phase(self, phase)

    @transaction.atomic
    def complete_quest(self, xp_gained):
        """
        Complete the character's active quest and apply rewards.
        """
        return character_services.character_complete_quest(self, xp_gained)

    @transaction.atomic
    def apply_quest_results(self, quest):
        """
        Apply the rewards associated with a character quest to the character, including
        coins, xp, and dynamic rewards.

        """
        return character_services.character_apply_quest_results(self, quest)

    @classmethod
    def has_available(cls):
        return character_services.character_has_available(cls)


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
    def end_at(self):
        return self.unlinked_at or timezone.now()

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
            is_complete=True,
            completed_at__gte=self.linked_at,
            completed_at__lte=self.end_at,
        )

        total_seconds = qs.aggregate(total=Sum("duration"))["total"] or 0
        return int(total_seconds // 60)

    def update_points(self):
        # Get or create link-specific currency
        currency = self.get_link_points_currency()
        last_calc = currency.last_calculated_at or self.linked_at

        # Only calculate points for overlapping period of this link
        period_start = max(last_calc, self.linked_at)
        period_end = self.end_at

        days_delta = max((period_end.date() - period_start.date()).days, 0)
        day_points = days_delta

        new_logins = self.player.user.logins.filter(
            timestamp__gt=period_start, timestamp__lte=period_end
        ).count()
        login_points = new_logins * 5

        new_activity_seconds = (
            self.character.activities.filter(
                is_complete=True,
                completed_at__gt=period_start,
                completed_at__lte=period_end,
            ).aggregate(total=Sum("duration"))["total"]
            or 0
        )
        time_points = (new_activity_seconds // 60) // 60

        total_new_points = day_points + login_points + time_points

        # Premium multiplier
        if self.player.user.subscription_status == "active":
            total_new_points *= 2

        # Credit currency
        currency.earn(total_new_points)
        return total_new_points

    def get_link_points_currency(self):
        return self.player.get_currency(f"link_points")

    @property
    def link_points(self):
        return self.get_link_points_currency().earned

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
    def deactivate_active_links(
        cls, player: Player = None, character: Character = None
    ):
        return link_services.player_link_deactivate_active_links(cls, player, character)

    @classmethod
    def assign_character(cls, player: Player, character: Character):
        return link_services.player_link_assign_character(cls, player, character)

    @classmethod
    def total_link_points(cls, list_of_links):
        return sum(link.link_points for link in list_of_links)
