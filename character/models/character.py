# from datetime import datetime
from django.db import models, transaction, IntegrityError
from django.utils.timezone import now
from django.utils import timezone
from random import random, randint
from typing import TYPE_CHECKING, Optional, Dict, Any, cast
import logging

from users.models import Person, Player

from gameplay.models import QuestCompletion, Quest
from gameplay.serializers import QuestResultSerializer
from progression.models import CharacterQuest
from progress_rpg.exceptions import QuestError

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
    created_at = models.DateTimeField(default=now)
    last_updated = models.DateTimeField(default=now)
    romantic_relationship = models.OneToOneField(
        "RomanticRelationship", on_delete=models.SET_NULL, null=True, blank=True
    )

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


class RomanticRelationship(models.Model):
    last_childbirth_date = models.DateField(null=True, blank=True)
    total_births = models.PositiveIntegerField(default=0)
    partner_is_pregnant = models.BooleanField(default=False)

    def __str__(self):
        return f"Partnership between {self.partner1} and {self.partner2}"


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
    fertility = models.IntegerField(default=50)
    last_childbirth_date = models.DateField(null=True, blank=True)
    is_pregnant = models.BooleanField(default=False)
    pregnancy_start_date = models.DateField(null=True, blank=True)
    pregnancy_due_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def get_age(self):
        return (now().date() - self.birth_date).days

    def die(self):
        self.death_date = now().date()
        self.save()

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
        self.pregnancy_start_date = now().date()
        self.pregnancy_partner = partner

        self.save()

    def handle_childbirth(self):
        child_name = f"Child of {self.first_name}"
        child = Character.objects.create(
            name=child_name,
            birth_date=now().date(),
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


class Character(Person, LifeCycleMixin):
    quest_completions = models.ManyToManyField(
        "gameplay.Quest",
        through="gameplay.QuestCompletion",
        related_name="completed_by",
    )
    total_quests = models.PositiveIntegerField(default=0)

    first_name = models.CharField(max_length=50, default="")
    last_name = models.CharField(max_length=50, default="", null=True, blank=True)
    backstory = models.TextField(default="")
    parents = models.ManyToManyField(
        "self", related_name="children", symmetrical=False, blank=True
    )
    sex = models.CharField(max_length=20, null=True)
    coins = models.PositiveIntegerField(default=0)
    reputation = models.IntegerField(default=0)
    can_link = models.BooleanField(default=False)
    position = models.OneToOneField(
        "locations.Position", on_delete=models.SET_NULL, null=True
    )
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
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def current_player(self):
        """
        Retrieve the player associated with this character.
        """
        return PlayerCharacterLink.get_player(self)

    def get_active_link(self):
        """Get active PlayerCharacterLink for this character."""
        return PlayerCharacterLink.objects.filter(
            character=self,
            is_active=True
        ).select_related('player').first()

    @property
    def player_is_online(self):
        """Check if linked player is online."""
        link = self.get_active_link()
        return link.player_is_online if link else False

    @property
    def xp_multiplier(self):
        """
        Get XP multiplier from link.
        
        Returns:
            float: 1.0 (offline), 2.0 (online)
        """
        link = self.get_active_link()
        return link.xp_multiplier if link else 1.0

    def on_player_state_change(self, now=None):
        """
        Called when player online/offline state changes.
        Interrupts current activity and starts a new one with current multiplier.
        
        This method handles both login and logout:
        1. Completes current activity early (with its stored multiplier)
        2. Starts new activity for remaining time (which captures current multiplier)
        
        Returns:
            CharacterActivity: The new activity (or None if none to interrupt)
        """
        now = now or timezone.now()
        
        behaviour = getattr(self, 'behaviour', None)
        if not behaviour:
            return None
        
        # Get current activity
        current = behaviour.sync_to_now(now)
        
        if not current or current.is_complete:
            return None
        
        # Don't interrupt sleep
        if current.kind == 'sleep':
            return current
        
        # Don't interrupt if less than 5 minutes remaining
        remaining = (current.scheduled_end - now).total_seconds()
        if remaining < 300:
            return current
        
        # Complete current activity early
        current.completed_at = now
        current.is_complete = True
        if current.started_at:
            current.duration = int((now - current.started_at).total_seconds())
        current.save()
        
        # Create new activity for remaining time
        # Multiplier will be captured automatically in save()
        from progression.models import CharacterActivity
        
        new_activity = CharacterActivity.objects.create(
            character=self,
            kind=current.kind,
            name=current.name or current.kind,
            scheduled_start=now,
            scheduled_end=current.scheduled_end,
            started_at=now,
            is_complete=False
        )
        
        return new_activity

    def start_quest(self, quest):
        self.quest_timer.change_quest(quest)

    @transaction.atomic
    def complete_quest(self, xp_gained):
        """
        Complete the character's active quest and apply rewards.

        Args:
            xp_gained: Experience points to award

        Returns:
            dict: Rewards summary including XP, coins, and level-ups

        Raises:
            QuestError: If no valid quest is found for completion
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
            self.total_quests += 1
            self.save(update_fields=["coins", "total_quests"])

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
        "users.Player", on_delete=models.CASCADE, related_name="character_link"
    )
    character = models.ForeignKey(
        "Character", on_delete=models.CASCADE, related_name="player_link"
    )
    date_linked = models.DateField(auto_now_add=True)
    date_unlinked = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    player_came_online_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the player came online while linked to this character"
    )

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
    def player_is_online(self):
        """Is the player currently connected?"""
        return self.player.is_online

    @property
    def xp_multiplier(self):
        """
        Simple multiplier: player online = 2.0x, offline = 1.0x
        
        Returns:
            float: 1.0 (offline), 2.0 (online)
        """
        return 2.0 if self.player_is_online else 1.0

    @classmethod
    def get_link_for_character(cls, character):
        """Get active link for a character."""
        return cls.objects.filter(
            character=character,
            is_active=True
        ).select_related('player').first()

    @classmethod
    def get_link_for_player(cls, player):
        """Get active link for a player."""
        return cls.objects.filter(
            player=player,
            is_active=True
        ).select_related('character').first()

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
        self.date_unlinked = now().date()
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
        # is_npc is now a property, so just update can_link
        character.can_link = False
        character.save(update_fields=["can_link"])
        return link


class CharacterRole(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.name}"


class CharacterRoleSkill(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    related_role = models.ForeignKey("CharacterRole", on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name}"


class CharacterProgression(models.Model):
    character = models.OneToOneField("character.Character", on_delete=models.CASCADE)
    role = models.ForeignKey(CharacterRole, on_delete=models.CASCADE)
    experience = models.IntegerField(default=0)

    base_progression_rate = models.PositiveIntegerField(default=1)
    player_acceleration_factor = models.PositiveIntegerField(default=2)
    date_started = models.DateField(default=now)

    def __str__(self):
        return f"{self.character.name} - {self.role.name}"

    def update_progression(self):
        time_elapsed = (now().date() - self.date_started).days
        new_experience = time_elapsed * self.base_progression_rate
        self.experience += new_experience

        if not self.character.is_npc:
            self.experience *= self.player_acceleration_factor

        self.save()
