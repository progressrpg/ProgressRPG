# from datetime import datetime
from django.db import models, transaction, IntegrityError
from django.utils.timezone import now
from random import random, randint
from typing import TYPE_CHECKING, Optional
import logging

from users.models import Person, Profile

from gameplay.models import Buff, AppliedBuff, QuestCompletion, Quest
from gameplay.serializers import QuestResultSerializer

if TYPE_CHECKING:
    from gameplay.models import QuestTimer

logger = logging.getLogger("django")


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
    buffs = models.ManyToManyField(
        "gameplay.Buff", related_name="characters", blank=True
    )
    is_npc = models.BooleanField(default=True)
    can_link = models.BooleanField(default=False)
    position = models.OneToOneField(
        "locations.Position", on_delete=models.SET_NULL, null=True
    )
    # quest_timer = Optional["QuestTimer"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def current_profile(self):
        """
        Retrieve the profile associated with this character.
        """
        return PlayerCharacterLink.get_profile(self)

    def start_quest(self, quest):
        self.quest_timer.change_quest(quest)

    def get_quest_completions(self, quest: Quest):
        return QuestCompletion.objects.filter(character=self, quest=quest)

    @transaction.atomic
    def complete_quest(self, xp_gained):
        logger.info(f"[CHAR.COMPLETE_QUEST] Starting quest completion for {self}")

        quest = self.quest_timer.quest
        logger.debug(f"{self.quest_timer}")

        if quest is None:
            logger.error(f"[CHAR.COMPLETE_QUEST] Quest is None for character {self.id}")
            return None

        try:
            completion, created = QuestCompletion.objects.get_or_create(
                character=self,
                quest=quest,
            )
            if not created:
                completion.times_completed += 1
                completion.save()

        except IntegrityError as e:
            logger.error(
                f"[CHAR.COMPLETE_QUEST] IntegrityError: failed to create or retrieve quest completion for character {self.id}, quest {quest.id}: {e}"
            )
            return None
        except Exception as e:
            logger.exception(
                f"[CHAR.COMPLETE_QUEST] Unexpected error while completing quest {quest.id} for character {self.id}: {e}"
            )
            return None

        rewards_summary = None
        try:
            if hasattr(quest, "results") and quest.results is not None:
                quest.results.apply(self)
                rewards_summary = QuestResultSerializer(quest.results).data

        except Exception as e:
            logger.exception(
                f"[CHAR.COMPLETE_QUEST] Error applying rewards for quest {quest.id}: {e}"
            )

        levelups = []
        try:
            levelups = self.add_xp(xp_gained)
            self.total_quests += 1
            self.save(update_fields=["total_quests"])

        except Exception as e:
            logger.exception(
                f"[CHAR.COMPLETE_QUEST] Error updating XP or quest count for character {self.id}: {e}"
            )
            return None

        try:
            from gameplay.models import ServerMessage

            for event in levelups:
                ServerMessage.objects.create(
                    group=self.current_profile.group_name,
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

        logger.info(f"[CHAR.COMPLETE_QUEST] Quest completion successful")
        return rewards_summary

    @classmethod
    def has_available(cls):
        return cls.objects.filter(is_npc=True, can_link=True).exists()


class PlayerCharacterLink(models.Model):
    profile = models.ForeignKey(
        "users.Profile", on_delete=models.CASCADE, related_name="character_link"
    )
    character = models.ForeignKey(
        "Character", on_delete=models.CASCADE, related_name="profile_link"
    )
    date_linked = models.DateField(auto_now_add=True)
    date_unlinked = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    @classmethod
    def get_character(cls, profile: Profile) -> Character:
        links = PlayerCharacterLink.objects.filter(profile=profile, is_active=True)
        if not links.exists():
            raise ValueError("No active Character found for this profile.")

        if links.count() > 1:
            logger.warning(
                f"[PROFILE] Multiple active characters found for profile {profile.id} — returning the first one"
            )

        return links.first().character

    @classmethod
    def get_profile(cls, character: Character) -> Profile:
        links = PlayerCharacterLink.objects.filter(character=character, is_active=True)
        if not links.exists():
            raise ValueError("Character has no active Profile link.")

        if links.count() > 1:
            logger.warning(
                f"[PROFILE] Multiple active profile links found for character {character.id} — returning the first one"
            )

        return links.first().profile

    def unlink(self):
        """Marks link as inactive and records unlink date"""
        self.date_unlinked = now().date()
        self.is_active = False
        self.save()

    @classmethod
    def deactivate_active_links(cls, profile: Profile):
        for link in cls.objects.filter(profile=profile, is_active=True):
            link.unlink()

    @classmethod
    def assign_character(cls, profile: Profile, character: Character):
        cls.deactivate_active_links(profile)
        link = cls.objects.create(
            profile=profile,
            character=character,
            is_active=True,
        )
        character.is_npc = False
        character.can_link = False
        character.save(update_fields=["is_npc", "can_link"])
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
