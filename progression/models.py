# progression/models.py
from decimal import Decimal
from datetime import timedelta
from django.apps import apps
from django.db import models, transaction
from django.db.models import CheckConstraint, Q, Sum
from django.utils import timezone
from typing import Dict, Any, cast
import logging

from .mixins import PlayerOwnedMixin
from character.phrases import generate_phrase

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
    group_key = models.CharField(max_length=255, null=True, blank=True, db_index=True)
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

    @staticmethod
    def _normalized_grouping_name(name: str | None) -> str:
        return (name or "").strip().casefold()

    @staticmethod
    def _history_last_seen(activity: "PlayerActivity"):
        return activity.completed_at or activity.last_updated or activity.created_at

    def _grouped_history(self):
        if not self.player_id:
            return []

        queryset = (
            self.__class__.objects.filter(player_id=self.player_id)
            .exclude(group_key__isnull=True)
            .exclude(group_key="")
            .only(
                "id", "name", "group_key", "completed_at", "last_updated", "created_at"
            )
        )

        if self.pk:
            queryset = queryset.exclude(pk=self.pk)

        return list(queryset)

    def infer_group_key(self) -> str | None:
        normalized_name = self._normalized_grouping_name(self.name)
        if not normalized_name:
            return None

        history = self._grouped_history()
        if not history:
            return None

        overall_stats: dict[str, dict[str, Any]] = {}
        exact_stats: dict[str, dict[str, Any]] = {}
        similar_stats: dict[str, dict[str, Any]] = {}

        for activity in history:
            if not activity.group_key:
                continue

            last_seen = self._history_last_seen(activity)
            group_key = activity.group_key
            existing_name = self._normalized_grouping_name(activity.name)

            overall_entry = overall_stats.setdefault(
                group_key,
                {"count": 0, "last_seen": last_seen},
            )
            overall_entry["count"] += 1
            if last_seen > overall_entry["last_seen"]:
                overall_entry["last_seen"] = last_seen

            if existing_name == normalized_name:
                exact_entry = exact_stats.setdefault(
                    group_key,
                    {"count": 0, "last_seen": last_seen},
                )
                exact_entry["count"] += 1
                if last_seen > exact_entry["last_seen"]:
                    exact_entry["last_seen"] = last_seen
                continue

            if existing_name and (
                normalized_name in existing_name or existing_name in normalized_name
            ):
                similar_entry = similar_stats.setdefault(
                    group_key,
                    {"count": 0, "last_seen": last_seen},
                )
                similar_entry["count"] += 1
                if last_seen > similar_entry["last_seen"]:
                    similar_entry["last_seen"] = last_seen

        def ranked_candidates(stats: dict[str, dict[str, Any]]):
            return sorted(
                (
                    {
                        "group_key": group_key,
                        "count": values["count"],
                        "overall_count": overall_stats[group_key]["count"],
                        "last_seen": values["last_seen"],
                    }
                    for group_key, values in stats.items()
                ),
                key=lambda candidate: (
                    -candidate["count"],
                    -candidate["overall_count"],
                    -candidate["last_seen"].timestamp(),
                ),
            )

        exact_candidates = ranked_candidates(exact_stats)
        if exact_candidates:
            return cast(str, exact_candidates[0]["group_key"])

        similar_candidates = ranked_candidates(similar_stats)
        if not similar_candidates:
            return None

        top_candidate = similar_candidates[0]
        top_last_seen = cast(timezone.datetime, top_candidate["last_seen"])
        if top_candidate["count"] < 3 or timezone.now() - top_last_seen > timedelta(
            days=120
        ):
            return None

        if len(similar_candidates) > 1:
            second_candidate = similar_candidates[1]
            if (
                top_candidate["count"] < second_candidate["count"] * 2
                or top_candidate["count"] - second_candidate["count"] < 2
            ):
                return None

        return cast(str, top_candidate["group_key"])

    def save(self, *args, **kwargs):
        if not self.group_key:
            inferred_group_key = self.infer_group_key()
            if inferred_group_key:
                self.group_key = inferred_group_key
                update_fields = kwargs.get("update_fields")
                if update_fields is not None:
                    kwargs["update_fields"] = set(update_fields) | {"group_key"}

        super().save(*args, **kwargs)

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

    def get_xp_reward_summary(self) -> Dict[str, Any]:
        base_xp = self.calculate_base_xp(self.duration)
        player = self.player
        multiplier = player.get_activity_xp_multiplier()
        multiplier_value = (
            int(multiplier)
            if multiplier == multiplier.to_integral_value()
            else float(multiplier)
        )
        return {
            "duration_seconds": self.duration,
            "base_xp": base_xp,
            "xp_multiplier": multiplier_value,
            "xp_gained": int(Decimal(base_xp) * multiplier),
        }

    def complete(self, reward_summary: Dict[str, Any] | None = None):
        """
        Mark the record as completed if not already complete.
        """
        if getattr(self, "is_complete", False):
            return self.xp_gained

        self.completed_at = timezone.now()
        self.is_complete = True
        reward_summary = reward_summary or self.get_xp_reward_summary()
        self.xp_gained = cast(int, reward_summary["xp_gained"])
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

        try:
            player = self.character.current_player
        except ValueError:
            player = None

        if player and player.is_online:
            village_state = getattr(self.character.population_centre, "state", "Stable")
            phrase = generate_phrase(village_state, self.kind, self.character)
            activity_name = (self.name or "activity").lower()
            message = f"{self.character.first_name} completed {activity_name}. {phrase}"

            ServerMessage = apps.get_model("gameplay", "ServerMessage")
            ServerMessage.objects.create(
                group=player.group_name,
                type="notification",
                action="notification",
                message=message,
                data={},
                is_draft=False,
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
