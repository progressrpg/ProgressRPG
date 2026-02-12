# progression/models.py
from decimal import Decimal
from asgiref.sync import async_to_sync
from django.db import models, transaction
from django.db.models import CheckConstraint, Q, Sum
from django.utils import timezone
from typing import Dict, Any, cast
import logging

from .mixins import PlayerOwnedMixin

from character.phrases import generate_phrase
from gameplay.utils import send_group_message


logger = logging.getLogger("general")


#########################################
#####      Group models
#########################################


class Group(models.Model):
    """
    Abstract base model for tracking groups of skills.
    """

    name = models.CharField(max_length=255)
    description = models.TextField(max_length=2000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    @property
    def total_time(self):
        return (
            self.skills.filter(records__is_complete=True).aggregate(
                total=Sum("records__duration")
            )["total"]
            or 0
        )

    @property
    def total_records(self):
        return (
            self.skills.filter(records__is_complete=True).aggregate(
                total=Sum("records")
            )["total"]
            or 0
        )

    @property
    def total_xp(self):
        return (
            self.skills.filter(records__is_complete=True).aggregate(
                total=Sum("records__xp_gained")
            )["total"]
            or 0
        )

    class Meta:
        abstract = True


class Category(Group, PlayerOwnedMixin):
    player = models.ForeignKey(
        "users.Player", on_delete=models.CASCADE, related_name="categories"
    )

    def __str__(self):
        return self.name


class Role(Group):
    character = models.ForeignKey(
        "character.Character", on_delete=models.CASCADE, related_name="roles"
    )

    def __str__(self):
        return self.name


#########################################
#####      Skill models
#########################################


class Skill(models.Model):
    """
    Abstract base model for tracking skills.
    """

    name = models.CharField(max_length=255)
    description = models.TextField(max_length=2000, blank=True)
    level = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    @property
    def total_time(self):
        return (
            self.records.filter(is_complete=True).aggregate(total=Sum("duration"))[
                "total"
            ]
            or 0
        )

    @property
    def total_records(self):
        return self.records.filter(is_complete=True).count()

    @property
    def total_xp(self):
        return (
            self.records.filter(is_complete=True).aggregate(total=Sum("xp_gained"))[
                "total"
            ]
            or 0
        )

    class Meta:
        abstract = True


class PlayerSkill(Skill, PlayerOwnedMixin):
    player = models.ForeignKey(
        "users.Player", on_delete=models.CASCADE, related_name="skills"
    )
    is_private = models.BooleanField(default=False)
    category = models.ForeignKey(
        "progression.Category",
        on_delete=models.SET_NULL,
        related_name="skills",
        null=True,
        blank=True,
    )

    def __str__(self):
        """
        Return a readable name for the skill, masking private ones.
        """
        if self.is_private:
            return f"Private skill ({self.player.name})"
        return f"{self.name} ({self.player.name})"


class CharacterSkill(Skill):
    character = models.ForeignKey(
        "character.Character", on_delete=models.CASCADE, related_name="skills"
    )
    roles = models.ManyToManyField(Role, related_name="skills")

    def __str__(self):
        return self.name


#########################################
#####      TimeRecord models
#########################################


class TimeRecord(models.Model):
    """
    Abstract base model for tracking time-based records, such as quests or activities.

    Stores metadata about start, completion, duration, and XP rewards.
    """

    name = models.CharField(max_length=255, blank=True)
    description = models.TextField(max_length=2000, blank=True)
    duration = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    is_complete = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    xp_gained = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def add_time(self, num: int):
        """
        Increase the record's duration by a given amount.
        """
        self.duration += num
        self.save(update_fields=["duration"])
        return self

    def new_time(self, num: int):
        """
        Set the record's duration to a new value.
        """
        self.duration = num
        self.save(update_fields=["duration"])
        return self

    def start(self):
        """
        Mark the record as started if not already started.
        """
        if getattr(self, "started_at", False):
            return
        self.started_at = timezone.now()
        self.save(update_fields=["started_at"])
        return self.started_at

    def complete(self):
        """
        Mark the record as completed if not already complete.
        """
        if getattr(self, "is_complete", False):
            return getattr(self, "completed_at", None)

        self.completed_at = timezone.now()
        self.is_complete = True
        self.save(update_fields=["completed_at", "is_complete"])

        return self.completed_at

    class Meta:
        abstract = True


class PlayerActivity(TimeRecord, PlayerOwnedMixin):
    """
    Represents an activity tracked by a user.

    Inherits common time tracking fields and behaviour from ``TimeRecord``.
    Activities may be linked to a skill or project, and can be private.
    """

    player = models.ForeignKey(
        "users.Player", on_delete=models.CASCADE, related_name="activities"
    )
    is_private = models.BooleanField(default=False)
    skill = models.ForeignKey(
        "progression.PlayerSkill",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="records",
    )
    project = models.ForeignKey(
        "progression.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="records",
    )
    task = models.ForeignKey(
        "progression.Task",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="records",
    )

    class Meta:
        ordering = ["-created_at"]
        db_table = "progression_activity"
        constraints = [
            CheckConstraint(
                condition=(Q(task__isnull=True) | Q(project__isnull=True)),
                name="activity_task_or_project_not_both",
            )
        ]

    def __str__(self):
        """
        Return a readable name for the activity, masking private ones.
        """
        return "Private activity" if self.is_private else f"activity {self.name}"

    def rename(self, newName):
        self.name = newName
        self.save(update_fields=["name"])

    def calculate_base_xp(self, duration: int) -> int:
        """
        Calculate and store the XP reward based on duration.
        Currently, XP gained equals total duration in seconds.
        """
        xp = duration
        return xp

    def complete(self):
        """
        Mark the record as completed if not already complete.
        """
        if getattr(self, "is_complete", False):
            return getattr(self, "completed_at", None)

        self.completed_at = timezone.now()
        self.is_complete = True
        base_xp = self.calculate_base_xp(self.duration)
        multiplier = self.player.get_xp_multiplier()
        self.xp_gained = int(Decimal(base_xp) * multiplier)
        self.save(update_fields=["completed_at", "is_complete", "xp_gained"])

        return self.xp_gained


class CharacterActivity(TimeRecord):
    """
    Character's autonomous activity.
    Generated daily, added to a queue, consumes character time.
    """

    scheduled_start = models.DateTimeField(null=True, blank=True)
    scheduled_end = models.DateTimeField(null=True, blank=True)

    character = models.ForeignKey(
        "character.Character",
        on_delete=models.CASCADE,
        related_name="activities",
    )
    kind = models.CharField(
        max_length=50,
        choices=[
            ("sleep", "Sleeping"),
            ("morning", "Morning routine"),
            ("work", "Working"),
            ("meal", "Meal"),
            ("leisure", "Leisure"),
            ("wind_down", "Wind down"),
            ("rest", "Resting"),
            ("idle", "Idling"),
        ],
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"character_activity {self.name}"

    def calculate_base_xp(self, duration: int) -> int:
        """
        Calculate and store the XP gained based on duration.
        """
        base_xp = duration // 60
        multiplier = 0.25 if self.kind == "rest" else 1
        return int(base_xp * multiplier)

    def complete_now(self):
        """
        Mark the activity as completed at the current time.
        """
        if self.started_at is None:
            self.started_at = self.scheduled_start

        now = timezone.now()
        self.completed_at = now
        self.is_complete = True

        duration = int((now - self.started_at).total_seconds())
        base_xp = self.calculate_base_xp(duration)
        multiplier = self.character.get_xp_multiplier()
        self.xp_gained = int(Decimal(base_xp) * multiplier)
        self.duration = duration

        self.save(
            update_fields=[
                "completed_at",
                "is_complete",
                "duration",
                "started_at",
                "xp_gained",
            ]
        )

        # --- Generate completion phrase ---
        player = self.character.current_player
        if player.is_online:
            village_state = getattr(
                self.character.population_centre, "state", "stable"
            )  # fallback
            phrase = generate_phrase(
                state=village_state, activity_type=self.kind, character=self.character
            )

            message = (
                f"{self.character.first_name} completed {self.name.lower()}. {phrase}"
            )
            async_to_sync(send_group_message)(
                player.group_name,
                {
                    "type": "notification",
                    "action": "notification",
                    "message": message,
                    "data": {},
                },
            )

        return self.xp_gained

    def complete_past(self):
        """
        Mark the activity as completed at the scheduled end time.
        """
        if self.started_at is None:
            self.started_at = self.scheduled_start

        self.completed_at = self.scheduled_end
        self.is_complete = True
        duration = max(0, int((self.scheduled_end - self.started_at).total_seconds()))
        self.duration = duration
        self.xp_gained = self.calculate_base_xp(duration)
        self.save(
            update_fields=[
                "completed_at",
                "is_complete",
                "duration",
                "started_at",
                "xp_gained",
            ]
        )
        return self.completed_at


class CharacterQuest(TimeRecord):
    """
    Represents a quest assigned to a character.

    Inherits common time tracking fields and behaviour from ``TimeRecord``.
    Includes extra narrative fields (intro/outro text), user-selected
    duration, and stage progression data.
    """

    character = models.ForeignKey(
        "character.Character", on_delete=models.CASCADE, related_name="character_quests"
    )
    skill = models.ForeignKey(
        "progression.CharacterSkill",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="records",
    )
    intro_text = models.TextField(max_length=2000, blank=True)
    outro_text = models.TextField(max_length=2000, blank=True)
    target_duration = models.PositiveIntegerField(default=0)
    stages = models.JSONField(
        default=list
    )  # use this to add stage: self.stages = self.stages + [new_stage]
    stages_fixed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"character_quest {self.name}"

    def calculate_base_xp(self) -> int:
        """
        Calculate and store the XP reward based on duration.

        Currently, XP gained equals total duration in seconds.
        """
        xp = self.duration
        return xp


#########################################
#####      Other models
#########################################


class Project(models.Model, PlayerOwnedMixin):
    player = models.ForeignKey(
        "users.Player", on_delete=models.CASCADE, related_name="projects"
    )
    name = models.CharField(max_length=100)
    description = models.TextField(max_length=2000, null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_complete = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    @property
    def total_time(self):
        return (
            PlayerActivity.objects.filter(
                Q(project=self) | Q(task__project=self),
                is_complete=True,
            ).aggregate(total=Sum("duration"))["total"]
            or 0
        )

    @property
    def total_records(self):
        return (
            PlayerActivity.objects.filter(
                Q(project=self) | Q(task__project=self),
                is_complete=True,
            ).count()
            or 0
        )

    def __str__(self):
        return self.name


class Task(models.Model, PlayerOwnedMixin):
    player = models.ForeignKey(
        "users.Player", on_delete=models.CASCADE, related_name="tasks"
    )
    project = models.ForeignKey(
        "progression.Project",
        on_delete=models.SET_NULL,
        related_name="tasks",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=100)
    description = models.TextField(max_length=2000, null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_complete = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    @property
    def total_time(self):
        return (
            self.records.filter(is_complete=True).aggregate(total=Sum("duration"))[
                "total"
            ]
            or 0
        )

    @property
    def total_records(self):
        return self.records.filter(is_complete=True).count()

    def __str__(self):
        return self.name
