# progression/models.py
from decimal import Decimal
from django.apps import apps
from django.db import models, transaction
from django.db.models import CheckConstraint, Q, Sum
from django.utils import timezone
from typing import Dict, Any, cast, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from django.db.models import Manager

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

    if TYPE_CHECKING:
        # Reverse FK added by concrete subclasses (Category) via each
        # Skill subclass's `related_name="skills"`.
        skills: "Manager[Any]"

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
        from .points import xp_for_duration

        total_duration = (
            self.skills.filter(records__is_complete=True).aggregate(
                total=Sum("records__duration")
            )["total"]
            or 0
        )
        return xp_for_duration(total_duration)

    class Meta:
        abstract = True


class Category(Group, PlayerOwnedMixin):
    player = models.ForeignKey(
        "users.Player", on_delete=models.CASCADE, related_name="categories"
    )

    def __str__(self):
        return self.name


#########################################
#####      Role / skill taxonomy models
#########################################


def _character_skill_duration(character, **skill_definition_filter):
    """
    Sum completed duration for a character across CharacterActivity records
    whose ActivityDefinition.skill matches the given SkillDefinition filter
    (e.g. role=<Role> or gate_group=<SkillGroup>; no filter = every skill).
    """
    filter_kwargs = {
        f"activity_definition__skill__{lookup}": value
        for lookup, value in skill_definition_filter.items()
    }
    return (
        CharacterActivity.objects.filter(
            character=character, is_complete=True, **filter_kwargs
        ).aggregate(total=Sum("duration"))["total"]
        or 0
    )


def _character_skill_proficiency(character, **skill_definition_filter):
    """
    XP earned by a character within the given SkillDefinition scope (see
    `_character_skill_duration`). Shared by `Role.proficiency_for` and
    `SkillGroup.proficiency_for` so both scopes use the same aggregation.
    """
    from .points import xp_for_duration

    return xp_for_duration(
        _character_skill_duration(character, **skill_definition_filter)
    )


def character_total_skill_xp(character) -> int:
    """
    A character's total skill XP across every skill - the "total XP" input
    to the AP mastery multiplier (see progression.points.xp_mastery_multiplier).
    """
    from .points import xp_for_duration

    return xp_for_duration(_character_skill_duration(character))


class Role(models.Model):
    """
    Authored role definition (e.g. "Farmer", "Guard") - not owned by any one
    character. Characters hold roles via `CharacterRole`; `SkillGroup` and
    `SkillDefinition` scope to a `Role` to build the skill taxonomy.
    """

    name = models.CharField(max_length=255)
    description = models.TextField(max_length=2000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def proficiency_for(self, character) -> int:
        return _character_skill_proficiency(character, role=self)


class SkillGroup(models.Model):
    """
    A named grouping of SkillDefinitions within a single Role, used as a
    gating scope (see `SkillDefinition.gate_group`).
    """

    role = models.ForeignKey(
        Role, on_delete=models.CASCADE, related_name="skill_groups"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(max_length=2000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.role.name})"

    def proficiency_for(self, character) -> int:
        return _character_skill_proficiency(character, gate_group=self)


class SkillDefinition(models.Model):
    """
    Authored definition of a skill a character can practice. `role` is
    nullable to allow general skills that aren't tied to any one role.
    `gate_group` + `min_proficiency` gate the skill on a SkillGroup's
    aggregate proficiency rather than on any specific prerequisite skill.
    """

    name = models.CharField(max_length=255)
    description = models.TextField(max_length=2000, blank=True)
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="skill_definitions",
        null=True,
        blank=True,
    )
    gate_group = models.ForeignKey(
        SkillGroup,
        on_delete=models.SET_NULL,
        related_name="gated_skill_definitions",
        null=True,
        blank=True,
    )
    min_proficiency = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def is_unlocked_for(self, character) -> bool:
        if self.gate_group_id is None or self.min_proficiency is None:
            return True
        return self.gate_group.proficiency_for(character) >= self.min_proficiency


class CharacterRole(models.Model):
    """
    Through model letting a character hold multiple Roles.
    """

    character = models.ForeignKey(
        "character.Character", on_delete=models.CASCADE, related_name="character_roles"
    )
    role = models.ForeignKey(
        Role, on_delete=models.CASCADE, related_name="character_roles"
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["character", "role"], name="unique_character_role"
            )
        ]

    def __str__(self):
        return f"{self.character} - {self.role}"


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

    if TYPE_CHECKING:
        # Reverse FK added by concrete subclasses (PlayerSkill) via each
        # TimeRecord subclass's `related_name="records"`.
        records: "Manager[Any]"

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
        from .points import xp_for_duration

        return xp_for_duration(self.total_time)

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


class CharacterSkill(models.Model):
    """
    A character's progress in a SkillDefinition. Time/XP totals are derived
    from the character's completed CharacterActivity records for this skill
    (via ActivityDefinition.skill) - the same source Role/SkillGroup
    proficiency aggregates over - rather than owning any TimeRecord of its
    own.
    """

    character = models.ForeignKey(
        "character.Character", on_delete=models.CASCADE, related_name="skills"
    )
    skill_definition = models.ForeignKey(
        SkillDefinition, on_delete=models.CASCADE, related_name="character_skills"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["character", "skill_definition"],
                name="unique_character_skill_definition",
            )
        ]

    def __str__(self):
        return f"{self.skill_definition.name} ({self.character})"

    def _matching_activities(self):
        return CharacterActivity.objects.filter(
            character=self.character,
            activity_definition__skill=self.skill_definition,
            is_complete=True,
        )

    @property
    def total_time(self):
        return (
            self._matching_activities().aggregate(total=Sum("duration"))["total"] or 0
        )

    @property
    def total_records(self):
        return self._matching_activities().count()

    @property
    def total_xp(self):
        from .points import xp_for_duration

        return xp_for_duration(self.total_time)


#########################################
#####      TimeRecord models
#########################################


class TimeRecord(models.Model):
    """
    Abstract base model for tracking time-based records, such as activities.

    Stores metadata about start, completion, and duration. Does not carry
    name/description - subclasses that need an editable label own that
    themselves (e.g. PlayerActivity); CharacterActivity instead points at an
    ActivityDefinition for its name.

    `duration` is the sole source of truth for Activity Points (AP) / skill
    Experience Points (XP) - see progression.points. `reward_breakdown` is a
    snapshot of the multiplier breakdown computed at completion time, kept
    for historical display only; it is never summed/read back to derive
    balances, so AP/XP stay recalculable if the formula changes later.
    """

    duration = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    is_complete = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    reward_breakdown = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    @property
    def xp_gained(self):
        """
        Kept for API/frontend compatibility with the old frozen column - the
        AP amount from this record's `reward_breakdown` snapshot, or None
        for a record that hasn't been completed yet.
        """
        return self.reward_breakdown.get("xp_gained")

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


class Activity(PlayerOwnedMixin):
    """
    A player's reusable activity "type" (e.g. "Write tests"). PlayerActivity
    sessions FK this explicitly rather than each owning a free-standing
    name, replacing the old fuzzy name-matching (group_key/infer_group_key).
    """

    player = models.ForeignKey(
        "users.Player", on_delete=models.CASCADE, related_name="activity_catalog"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(max_length=2000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        # progression_activity is already claimed by PlayerActivity's legacy
        # explicit db_table.
        db_table = "progression_activity_catalog"
        constraints = [
            models.UniqueConstraint(
                fields=["player", "name"], name="unique_player_activity_name"
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.player.name})"

    @classmethod
    def get_or_create_for_player(cls, player, name: str) -> "Activity":
        normalized_name = name.strip()
        existing = cls.objects.filter(
            player=player, name__iexact=normalized_name
        ).first()
        if existing:
            return existing
        return cls.objects.create(player=player, name=normalized_name)


class SuggestedActivity(models.Model):
    """
    Authored, curated catalog for activity-name autocomplete - no FK to any
    player's data, so player-typed activity names (see Activity) stay
    private.
    """

    name = models.CharField(max_length=255)
    description = models.TextField(max_length=2000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class PlayerActivity(TimeRecord, PlayerOwnedMixin):
    """
    Represents an activity session tracked by a user.

    Inherits common time tracking fields and behaviour from ``TimeRecord``.
    Sessions may be linked to a skill or project, and can be private.
    """

    name = models.CharField(max_length=255, blank=True)
    description = models.TextField(max_length=2000, blank=True)
    player = models.ForeignKey(
        "users.Player", on_delete=models.CASCADE, related_name="activities"
    )
    activity = models.ForeignKey(
        Activity,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sessions",
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

    def save(self, *args, **kwargs):
        if not self.activity_id and self.player_id and self.name.strip():
            self.activity = Activity.get_or_create_for_player(self.player, self.name)
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                kwargs["update_fields"] = set(update_fields) | {"activity"}

        super().save(*args, **kwargs)

    def rename(self, newName):
        self.name = newName
        update_fields = ["name"]
        if newName.strip() and self.player_id:
            self.activity = Activity.get_or_create_for_player(self.player, newName)
            update_fields.append("activity")
        self.save(update_fields=update_fields)

    def calculate_base_xp(self, duration: int) -> int:
        from .points import base_rate

        return int(Decimal(duration) * base_rate())

    def get_xp_reward_summary(self) -> Dict[str, Any]:
        """
        Compute this activity's Activity Points (AP, still keyed "xp_gained"
        for API/frontend compatibility) and skill XP (if `skill` is set)
        breakdown for the current `duration` - live-derived from duration +
        the current formula/settings (see TimeRecord docs).
        """
        from .points import xp_for_duration, xp_mastery_multiplier

        base_xp = self.calculate_base_xp(self.duration)
        player = self.player
        multiplier = player.get_activity_xp_multiplier()
        task_xp_multiplier = Decimal("1.0")
        if self.task_id:
            from core.models import GameSettings

            task_xp_multiplier = GameSettings.current().task_activity_xp_multiplier
            multiplier *= task_xp_multiplier
        # Players have no skill XP source yet (see progression.points), so
        # this always evaluates to 1.0 - kept explicit here rather than
        # hardcoded so it picks up a real total once player skills exist.
        mastery_multiplier = xp_mastery_multiplier(0)
        multiplier *= mastery_multiplier

        def _fmt(d: Decimal) -> int | float:
            return int(d) if d == d.to_integral_value() else float(d)

        return {
            "duration_seconds": self.duration,
            "base_xp": base_xp,
            "xp_multiplier": _fmt(multiplier),
            "task_xp_multiplier": _fmt(task_xp_multiplier),
            "mastery_multiplier": _fmt(mastery_multiplier),
            "xp_gained": int(Decimal(base_xp) * multiplier),
            "skill_xp_gained": (xp_for_duration(self.duration) if self.skill_id else 0),
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
        self.reward_breakdown = reward_summary
        self.save(update_fields=["completed_at", "is_complete", "reward_breakdown"])

        return cast(int, reward_summary["xp_gained"])


class ActivityDefinition(models.Model):
    """
    Authored definition of a scheduled block a character's day can be made
    of. Fully uniform: every CharacterActivity - work as well as sleep,
    meals, and other routine blocks - points at one of these rather than
    owning its own name/kind.
    """

    class Kind(models.TextChoices):
        SLEEP = "sleep", "Sleeping"
        MORNING = "morning", "Morning routine"
        WORK = "work", "Working"
        MEAL = "meal", "Meal"
        LEISURE = "leisure", "Leisure"
        WIND_DOWN = "wind_down", "Wind down"
        REST = "rest", "Resting"
        IDLE = "idle", "Idling"

    name = models.CharField(max_length=255)
    description = models.TextField(max_length=2000, blank=True)
    kind = models.CharField(max_length=50, choices=Kind.choices)
    skill = models.ForeignKey(
        SkillDefinition,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_definitions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


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
    activity_definition = models.ForeignKey(
        ActivityDefinition,
        on_delete=models.PROTECT,
        related_name="character_activities",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"character_activity {self.activity_definition.name}"

    @property
    def name(self) -> str:
        return self.activity_definition.name

    @property
    def kind(self) -> str:
        return self.activity_definition.kind

    def get_xp_reward_summary(self) -> Dict[str, Any]:
        """
        Compute this activity's Activity Points (AP, still keyed "xp_gained"
        for API/frontend compatibility) and skill XP (if activity_definition.skill
        is set) breakdown for the current `duration` - live-derived from
        duration + the current formula/settings, never read back to derive
        balances (see TimeRecord docs).
        """
        from .points import base_rate, xp_for_duration, xp_mastery_multiplier

        rate = base_rate()
        kind_multiplier = (
            Decimal("0.25")
            if self.kind == ActivityDefinition.Kind.REST
            else Decimal("1")
        )
        boost_multiplier = self.character.get_xp_multiplier()
        mastery_multiplier = xp_mastery_multiplier(
            character_total_skill_xp(self.character)
        )
        base_xp = Decimal(self.duration) * rate
        multiplier = kind_multiplier * boost_multiplier * mastery_multiplier

        def _fmt(d: Decimal) -> int | float:
            return int(d) if d == d.to_integral_value() else float(d)

        return {
            "duration_seconds": self.duration,
            "base_xp": _fmt(base_xp),
            "xp_multiplier": _fmt(multiplier),
            "kind_multiplier": _fmt(kind_multiplier),
            "boost_multiplier": _fmt(boost_multiplier),
            "mastery_multiplier": _fmt(mastery_multiplier),
            "xp_gained": int(base_xp * multiplier),
            "skill_xp_gained": (
                xp_for_duration(self.duration)
                if self.activity_definition.skill_id is not None
                else 0
            ),
        }

    def _finish(self, reward_summary: Dict[str, Any]) -> int:
        self.reward_breakdown = reward_summary
        self.save(
            update_fields=[
                "completed_at",
                "is_complete",
                "duration",
                "started_at",
                "reward_breakdown",
            ]
        )
        ap_gained = cast(int, reward_summary["xp_gained"])
        self.character.add_xp(ap_gained)
        return ap_gained

    def complete_now(self):
        """
        Mark the activity as completed at the current time.
        """
        now = timezone.now()
        if self.started_at is None:
            self.started_at = self.scheduled_start or now

        self.completed_at = now
        self.is_complete = True
        self.duration = int((now - self.started_at).total_seconds())

        ap_gained = self._finish(self.get_xp_reward_summary())

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

        return ap_gained

    def complete_past(self):
        """
        Mark the activity as completed at the scheduled end time.
        """
        now = timezone.now()
        if self.started_at is None:
            self.started_at = self.scheduled_start or now

        self.completed_at = self.scheduled_end or now
        self.is_complete = True
        self.duration = max(
            0, int((self.completed_at - self.started_at).total_seconds())
        )

        self._finish(self.get_xp_reward_summary())
        return self.completed_at


#########################################
#####      Other models
#########################################


class Project(PlayerOwnedMixin):
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


class Task(PlayerOwnedMixin):
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
    first_completed_at = models.DateTimeField(null=True, blank=True)

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
    def last_worked_on(self):
        """Return the timestamp of the most recently completed linked activity."""
        latest_record = (
            self.records.filter(is_complete=True)
            .order_by("-completed_at", "-last_updated", "-created_at")
            .only("completed_at", "last_updated", "created_at")
            .first()
        )

        if not latest_record:
            return None

        return (
            latest_record.completed_at
            or latest_record.last_updated
            or latest_record.created_at
        )

    def __str__(self):
        return self.name
