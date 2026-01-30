# from datetime import datetime
from celery import current_app
from decimal import Decimal
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
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

from locations.models import Movable, Node, Building

if TYPE_CHECKING:
    from gameplay.models import QuestTimer

logger = logging.getLogger("general")
logger_errors = logging.getLogger("errors")


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
        self.strength = max(min(self.strength + amount, 100), -100)
        self.save()

    def log_event(self, event):
        """Add an event to the history log."""
        self.history.setdefault("events", []).append(event)
        self.save()

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
        return (timezone.now().date() - self.birth_date).days

    def die(self):
        self.death_date = timezone.now().date()
        self.save(update_fields=["death_date"])
        self.cancel_journey()

    def is_alive(self):
        return self.death_date is None

    def get_romantic_partners(self):
        return Character.objects.filter(
            characterrelationshipmembership__character=self,
            characterrelationshipmembership__relationship__relationship_type="romantic",
        )

    def is_fertile(self):
        return self.fertility > 0

    def can_reproduce_with(self, partner):
        if self.fertility <= 0 or partner.fertility <= 0:
            return False
        if (
            self.sex == "Male"
            and partner.sex == "Male"
            or self.sex == "Female"
            and partner.sex == "Female"
        ):
            return False
        return True

    def attempt_pregnancy(self):
        romantic_partners = self.get_romantic_partners()

        for partner in romantic_partners:
            if self.can_reproduce_with(partner):
                if self.is_fertile() and not self.is_pregnant:
                    self.start_pregnancy(partner)
                    return True
        return False

    def start_pregnancy(self, partner):
        self.is_pregnant = True
        self.pregnancy_start_date = timezone.now().date()
        self.pregnancy_partner = partner

        self.save()

    def handle_childbirth(self):
        child_name = f"Child of {self.first_name}"
        child = Character.objects.create(
            name=child_name,
            birth_date=timezone.now().date(),
            sex="Male" if randint(0, 1) == 0 else "Female",
            # x_coordinate=self.x_coordinate,
            # y_coordinate=self.y_coordinate,
        )

        child.parents.add(self)
        if self.pregnancy_partner:
            child.parents.add(self.pregnancy_partner)
        child.save()

    def handle_miscarriage(self):
        self.is_pregnant = False
        self.pregnancy_start_date = None
        self.save()

    def get_miscarriage_change(self):
        chance = 0.05
        if self.get_age() > (40 * 365):
            chance += 0.10
        return round(chance, 5)


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
    building = models.ForeignKey(
        "locations.Building",
        related_name="residents",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    population_centre = models.ForeignKey(
        "locations.PopulationCentre",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="residents",
    )

    parents = models.ManyToManyField(
        "self", related_name="children", symmetrical=False, blank=True
    )
    sex = models.CharField(
        max_length=20, choices=SexChoices.choices, null=True, blank=True
    )
    coins = models.PositiveIntegerField(default=0)
    reputation = models.IntegerField(default=0)
    can_link = models.BooleanField(default=False)
    # quest_timer = Optional["QuestTimer"]

    @property
    def is_npc(self):
        """
        A character is an NPC if they don't have an active PlayerCharacterLink.
        """
        return not self.player_link.filter(is_active=True).exists()

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
        if phase == "dawn":
            print(f"{self.name} wakes up and moves outside")
            self.go_outside(radius=10)
        elif phase == "day":
            print(f"{self.name} is outside during the day")
        elif phase == "dusk":
            print(f"{self.name} heads inside for the night")
            self.go_home()
        elif phase == "night":
            print(f"{self.name} is indoors at night")

    def assign_home(self, building: Building):
        self.building = building
        self.population_centre = building.population_centre
        self.save(update_fields=["building", "population_centre"])

    def go_home(self):
        if not self.building:
            print(f"{self.name} has no home to go to!")
            return

        destination_node = self.building.node.first()
        if not destination_node:
            print(f"{self.name} has no node! Skipping.")
            return

        if self.current_node == destination_node:
            print(f"{self.name} cannot go home, they're already there!")
            return

        rooms = self.building.interior_spaces.all()
        room = random.choice(rooms) if rooms else None
        if room:
            destination_node = room.nodes.first() or destination_node
        self.set_destination(node=destination_node)
        print(f"{self.name} is going home.")

    def get_outside_nodes(self):
        """
        Return outside nodes in the same population centre.
        """
        if not self.building or not self.building.population_centre:
            return Node.objects.none()

        return Node.objects.filter(
            population_centre=self.building.population_centre,
            kind=Node.Kind.OUTSIDE,
        )

    def pick_random_outside_node(self, radius=100):
        qs = self.get_outside_nodes()

        if self.location:
            qs = (
                qs.annotate(dist=Distance("location", self.location))
                .filter(dist__lte=radius)
                .order_by("dist")
            )

        nodes = list(qs)
        if not nodes:
            return None

        # weighted randomness: closer nodes more likely
        return random.choice(nodes[: max(3, len(nodes))])

    def go_outside(self, radius=100):
        node = self.pick_random_outside_node(radius=radius)
        if not node:
            print(f"{self.name} couldn't find anywhere to go outside")
            return False

        self.set_destination(node=node)
        return True

    def start_quest(self, quest):
        self.quest_timer.change_quest(quest)

    @transaction.atomic
    def complete_quest(self, xp_gained):
        """
        Complete the character's active quest and apply rewards.
        """
        logger.info(f"[CHAR.COMPLETE_QUEST] Starting quest completion for {self}")

        quest = self.quest_timer.quest

        if quest is None:
            logger_errors.error(
                f"[CHAR.COMPLETE_QUEST] Quest is None for character {self.id}",
                extra={"character_id": self.id},
            )
            raise QuestError(f"No quest found for character {self.id}")

        rewards_summary = None
        try:
            if hasattr(quest, "results") and quest.results is not None:
                rewards_summary = self.apply_quest_results(quest)
            else:
                rewards_summary = {
                    "xp_gained": 0,
                    "coins_gained": 0,
                    "dynamic_rewards": {},
                    "levelups": [],
                }
        except Exception as e:
            logger_errors.exception(
                f"[CHAR.COMPLETE_QUEST] Error applying rewards for quest {quest.id}: {e}"
            )

        logger.info(f"[CHAR.COMPLETE_QUEST] Quest completion successful")
        return rewards_summary

    @transaction.atomic
    def apply_quest_results(self, quest):
        """
        Apply the rewards associated with a character quest to the character, including
        coins, xp, and dynamic rewards.

        """
        logger.info(f"[QUESTRESULTS.APPLY] Applying results to character {self.name}")
        results = getattr(quest, "results", {}) or {}

        xp_rate = getattr(results, "xp_rate", 1)

        time_xp = xp_rate * getattr(quest, "duration", 0)
        level_scaling = 1
        repeat_penalty = 1
        final_xp = time_xp * level_scaling * repeat_penalty

        coins_gained = results.get("coin_reward", 0)
        self.coins += coins_gained

        dynamic_rewards = results.get("dynamic_rewards", {})
        if dynamic_rewards:
            for key, value in dynamic_rewards.items():
                if hasattr(self, f"apply_{key}"):
                    getattr(self, f"apply_{key}")(value)
                elif hasattr(self, key):
                    current_value = getattr(self, key)
                    if isinstance(current_value, (int, float)):
                        setattr(self, key, current_value + value)
                    else:
                        setattr(self, key, value)
        else:
            logger.info(
                f"[CHAR.APPLY_QUEST_RESULTS] No dynamic rewards found for quest."
            )

        levelups = []
        try:
            levelups = self.add_xp(final_xp)
            self.save(update_fields=["coins"])

        except Exception as e:
            logger.exception(
                f"[CHAR.APPLY_QUEST_RESULTS] Error updating XP or quest count for character {self.id}: {e}"
            )
            return None

        try:
            from gameplay.models import ServerMessage

            for event in levelups:
                ServerMessage.objects.create(
                    group=self.current_player.group_name,
                    type="notification",
                    action="notification",
                    message=f"Character {self.name} levelled up! Now level {event['new_level']}.",
                    data={"level": event["new_level"]},
                    is_draft=False,
                )
        except Exception as e:
            logger.exception(
                f"[CHAR.COMPLETE_QUEST] Error notifying levelup for character {self.id}: {e}"
            )
            return None
        rewards_summary = {
            "xp_gained": final_xp if "final_xp" in locals() else 0,
            "coins_gained": getattr(results, "coin_reward", 0) if results else 0,
            "dynamic_rewards": (
                getattr(results, "dynamic_rewards", {}) if results else {}
            ),
            "levelups": (
                [{"new_level": e["new_level"]} for e in levelups]
                if "levelups" in locals()
                else []
            ),
        }

        return rewards_summary

    @classmethod
    def has_available(cls):
        return (
            cls.objects.filter(can_link=True)
            .exclude(player_link__is_active=True)
            .exists()
        )


class PlayerCharacterLink(models.Model):
    player = models.ForeignKey(
        "users.Player", on_delete=models.CASCADE, related_name="links"
    )
    character = models.ForeignKey(
        "Character", on_delete=models.CASCADE, related_name="links"
    )
    date_linked = models.DateField(auto_now_add=True)
    date_unlinked = models.DateField(null=True, blank=True)
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

    @classmethod
    def get_character(cls, player: Player) -> Character:
        links = PlayerCharacterLink.objects.filter(player=player, is_active=True)
        if not links.exists():
            raise ValueError("No active Character found for this player.")

        if links.count() > 1:
            logger.warning(
                f"[PLAYER] Multiple active characters found for player {player.id} — returning the first one"
            )

        return links.first().character

    @classmethod
    def get_player(cls, character: Character) -> Player:
        links = PlayerCharacterLink.objects.filter(character=character, is_active=True)
        if not links.exists():
            raise ValueError("Character has no active Player link.")

        if links.count() > 1:
            logger.warning(
                f"[PLAYER] Multiple active player links found for character {character.id} — returning the first one"
            )

        return links.first().player

    def unlink(self):
        """Marks link as inactive and records unlink date"""
        self.date_unlinked = timezone.now().date()
        self.is_active = False
        self.save()
        # Make character available for linking again
        self.character.can_link = True
        self.character.save(update_fields=["can_link"])

    @classmethod
    def deactivate_active_links(cls, player: Player):
        for link in cls.objects.filter(player=player, is_active=True):
            link.unlink()

    @classmethod
    def deactivate_active_links_for_character(cls, character: Character):
        for link in cls.objects.filter(character=character, is_active=True):
            link.unlink()

    @classmethod
    def assign_character(cls, player: Player, character: Character):
        cls.deactivate_active_links(player)
        cls.deactivate_active_links_for_character(character)
        link = cls.objects.create(
            player=player,
            character=character,
            is_active=True,
        )
        character.can_link = False
        character.save(update_fields=["can_link"])
        return link
