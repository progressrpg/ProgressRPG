# progression/models.py
from django.db import models
from django.utils import timezone


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
        return self.skills.aggregate(total=Sum("total_time"))["total"] or 0

    @property
    def total_records(self):
        return self.skills.aggregate(total=Sum("total_records"))["total"] or 0

    @property
    def total_xp(self):
        return self.skills.aggregate(total=Sum("xp"))["total"] or 0

    def rename(self, new_name: str):
        """
        Update name.
        """
        self.name = new_name
        self.save(update_fields=["name"])
        return self

    class Meta:
        abstract = True


class Category(Group):
    profile = models.ForeignKey(
        "users.Profile", on_delete=models.CASCADE, related_name="categories"
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
        return self.records.aggregate(total=Sum("total_time"))["total"] or 0

    @property
    def total_records(self):
        return self.records.aggregate(total=Sum("total_records"))["total"] or 0

    @property
    def total_xp(self):
        return self.records.aggregate(total=Sum("xp"))["total"] or 0

    def rename(self, new_name: str):
        """
        Update the skill's  name.
        """
        self.name = new_name
        self.save(update_fields=["name"])
        return self

    class Meta:
        abstract = True


class PlayerSkill(Skill):
    profile = models.ForeignKey(
        "users.Profile", on_delete=models.CASCADE, related_name="skills"
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
            return f"Private skill ({self.profile.name})"
        return f"{self.name} ({self.profile.name})"


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

    name = models.CharField(max_length=255)
    description = models.TextField(max_length=2000, blank=True)
    duration = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    is_complete = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    xp_gained = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def rename(self, new_name: str):
        """
        Update the record's name.
        """
        self.name = new_name
        self.save(update_fields=["name"])
        return self

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

        skill = getattr(self, "skill", None)
        if skill:
            self.skill.add_record(1, time=getattr(self, "duration", 0))
        return self.completed_at

    def calculate_xp_reward(self) -> int:
        """
        Calculate and store the XP reward based on duration.

        Currently, XP gained equals total duration.
        """
        xp = self.duration
        return xp

    class Meta:
        abstract = True


class Activity(TimeRecord):
    """
    Represents an activity tracked by a user.

    Inherits common time tracking fields and behaviour from ``TimeRecord``.
    Activities may be linked to a skill or project, and can be private.
    """

    profile = models.ForeignKey(
        "users.Profile", on_delete=models.CASCADE, related_name="activities"
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

    def __str__(self):
        """
        Return a readable name for the activity, masking private ones.
        """
        return "Private activity" if self.is_private else f"activity {self.name}"


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


#########################################
#####      Other models
#########################################


class Project(models.Model):
    profile = models.ForeignKey(
        "users.Profile", on_delete=models.CASCADE, related_name="projects"
    )
    name = models.CharField(max_length=100)
    description = models.TextField(max_length=2000)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_time(self):
        return self.records.aggregate(total=Sum("total_time"))["total"] or 0

    @property
    def total_records(self):
        return self.records.aggregate(total=Sum("total_records"))["total"] or 0

    def __str__(self):
        return self.name


class Task(models.Model):
    profile = models.ForeignKey(
        "users.Profile", on_delete=models.CASCADE, related_name="tasks"
    )
    project = models.ForeignKey(
        "progression.Project",
        on_delete=models.SET_NULL,
        related_name="tasks",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=100)
    description = models.TextField(max_length=2000)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_time(self):
        return self.records.aggregate(total=Sum("total_time"))["total"] or 0

    @property
    def total_records(self):
        return self.records.aggregate(total=Sum("total_records"))["total"] or 0

    def __str__(self):
        return self.name
