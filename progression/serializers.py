# progression/serializers.py

from typing import cast

from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from django.utils.html import strip_tags
from rest_framework import serializers

from users.models import Player

from .models import (
    Category,
    Role,
    SkillGroup,
    SkillDefinition,
    CharacterRole,
    PlayerSkill,
    CharacterSkill,
    Activity,
    SuggestedActivity,
    PlayerActivity,
    ActivityDefinition,
    CharacterActivity,
    Project,
    Task,
    Note,
)

#########################################
#####      Base serializers
#########################################


class GroupBaseSerializer(serializers.ModelSerializer):
    total_time = serializers.IntegerField(read_only=True)
    total_records = serializers.IntegerField(read_only=True)
    total_xp = serializers.IntegerField(read_only=True)

    class Meta:
        fields = [
            "id",
            "name",
            "description",
            "created_at",
            "last_updated",
            "total_time",
            "total_records",
            "total_xp",
        ]
        abstract = True


class SkillBaseSerializer(serializers.ModelSerializer):
    total_time = serializers.IntegerField(read_only=True)
    total_records = serializers.IntegerField(read_only=True)
    total_xp = serializers.IntegerField(read_only=True)

    class Meta:
        fields = [
            "id",
            "name",
            "description",
            "level",
            "created_at",
            "last_updated",
            "total_time",
            "total_records",
            "total_xp",
        ]
        abstract = True


class TimeRecordBaseSerializer(serializers.ModelSerializer):
    xp_gained = serializers.ReadOnlyField()

    class Meta:
        fields = [
            "id",
            "name",
            "description",
            "duration",
            "started_at",
            "is_complete",
            "completed_at",
            "xp_gained",
            "reward_breakdown",
            "created_at",
            "last_updated",
        ]
        abstract = True


#########################################
#####      Group serializers
#########################################


class CategorySerializer(GroupBaseSerializer):
    player: serializers.PrimaryKeyRelatedField[Player] = (
        serializers.PrimaryKeyRelatedField(read_only=True)
    )

    class Meta(GroupBaseSerializer.Meta):
        model = Category
        fields = GroupBaseSerializer.Meta.fields + ["player"]
        read_only_fields = ["player"]


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "name", "description", "created_at", "last_updated"]


class SkillGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = SkillGroup
        fields = ["id", "role", "name", "description", "created_at", "last_updated"]


class SkillDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SkillDefinition
        fields = [
            "id",
            "name",
            "description",
            "role",
            "gate_group",
            "min_proficiency",
            "created_at",
            "last_updated",
        ]


class CharacterRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CharacterRole
        fields = ["id", "character", "role", "assigned_at"]


#########################################
#####      Skill serializers
#########################################


class PlayerSkillSerializer(SkillBaseSerializer):
    player: serializers.PrimaryKeyRelatedField[Player] = (
        serializers.PrimaryKeyRelatedField(read_only=True)
    )

    class Meta(SkillBaseSerializer.Meta):
        model = PlayerSkill
        fields = SkillBaseSerializer.Meta.fields + ["player", "is_private", "category"]
        read_only_fields = ["player"]


class CharacterSkillSerializer(serializers.ModelSerializer):
    total_time = serializers.IntegerField(read_only=True)
    total_records = serializers.IntegerField(read_only=True)
    total_xp = serializers.IntegerField(read_only=True)

    class Meta:
        model = CharacterSkill
        fields = [
            "id",
            "character",
            "skill_definition",
            "created_at",
            "last_updated",
            "total_time",
            "total_records",
            "total_xp",
        ]


#########################################
#####      TimeRecord serializers
#########################################


class ActivityDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityDefinition
        fields = [
            "id",
            "name",
            "present_tense",
            "description",
            "kind",
            "skill",
            "created_at",
            "last_updated",
        ]


class ActivitySerializer(serializers.ModelSerializer):
    player: serializers.PrimaryKeyRelatedField[Player] = (
        serializers.PrimaryKeyRelatedField(read_only=True)
    )

    class Meta:
        model = Activity
        fields = [
            "id",
            "player",
            "name",
            "description",
            "created_at",
            "last_updated",
        ]
        read_only_fields = ["player"]


class SuggestedActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = SuggestedActivity
        fields = ["id", "name", "description", "created_at", "last_updated"]


class PlayerActivitySerializer(TimeRecordBaseSerializer):
    player: serializers.PrimaryKeyRelatedField[Player] = (
        serializers.PrimaryKeyRelatedField(read_only=True)
    )

    class Meta(TimeRecordBaseSerializer.Meta):
        model = PlayerActivity
        fields = TimeRecordBaseSerializer.Meta.fields + [
            "player",
            "activity",
            "is_private",
            "origin",
            "skill",
            "project",
            "task",
        ]
        read_only_fields = ["player", "origin", "activity"]


class OfflineActivityLogSerializer(serializers.Serializer):
    """
    Validates a request to manually log a completed activity after the
    fact (offline logging, issue #630). ``skill``/``task`` are scoped to
    the requesting player to prevent referencing another player's records.
    """

    name = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )
    description = serializers.CharField(
        max_length=2000, required=False, allow_blank=True, default=""
    )
    skill = serializers.PrimaryKeyRelatedField(queryset=PlayerSkill.objects.none())
    task = serializers.PrimaryKeyRelatedField(queryset=Task.objects.none())
    started_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        player = getattr(getattr(request, "user", None), "player", None)
        skill_field = cast(serializers.PrimaryKeyRelatedField, self.fields["skill"])
        skill_field.queryset = (
            PlayerSkill.objects.filter(player=player)
            if player
            else PlayerSkill.objects.none()
        )
        skill_field.required = False
        skill_field.allow_null = True
        task_field = cast(serializers.PrimaryKeyRelatedField, self.fields["task"])
        task_field.queryset = (
            Task.objects.filter(player=player) if player else Task.objects.none()
        )
        task_field.required = False
        task_field.allow_null = True

    def validate(self, attrs):
        if not attrs.get("name") and not attrs.get("task"):
            raise serializers.ValidationError(
                "Provide a name (to create a new task) or an existing task to log against."
            )
        if attrs["completed_at"] <= attrs["started_at"]:
            raise serializers.ValidationError("completed_at must be after started_at.")
        return attrs


class CharacterActivitySerializer(serializers.ModelSerializer):
    name = serializers.ReadOnlyField()
    kind = serializers.ReadOnlyField()
    xp_gained = serializers.ReadOnlyField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = CharacterActivity
        fields = [
            "id",
            "character",
            "activity_definition",
            "name",
            "kind",
            "duration",
            "started_at",
            "is_complete",
            "completed_at",
            "xp_gained",
            "reward_breakdown",
            "created_at",
            "last_updated",
            "scheduled_start",
            "scheduled_end",
            "status",
        ]

    def get_status(self, obj) -> str:
        now = timezone.now()
        if obj.is_complete:
            return "past"
        if obj.scheduled_start and obj.scheduled_end:
            if obj.scheduled_start <= now < obj.scheduled_end:
                return "current"
            if now < obj.scheduled_start:
                return "future"
        return "unknown"


#########################################
#####      Other serializers
#########################################


class ProjectSerializer(serializers.ModelSerializer):
    player: serializers.PrimaryKeyRelatedField[Player] = (
        serializers.PrimaryKeyRelatedField(read_only=True)
    )
    total_time = serializers.IntegerField(read_only=True)
    total_records = serializers.IntegerField(read_only=True)

    class Meta:
        model = Project
        fields = [
            "id",
            "name",
            "description",
            "player",
            "created_at",
            "last_updated",
            "is_complete",
            "completed_at",
            "total_time",
            "total_records",
        ]


class TaskSerializer(serializers.ModelSerializer):
    player: serializers.PrimaryKeyRelatedField[Player] = (
        serializers.PrimaryKeyRelatedField(read_only=True)
    )
    total_time = serializers.IntegerField(read_only=True)
    total_records = serializers.IntegerField(read_only=True)
    last_worked_on = serializers.DateTimeField(read_only=True)
    subtask_count = serializers.IntegerField(source="subtasks.count", read_only=True)

    class Meta:
        model = Task
        fields = [
            "id",
            "name",
            "description",
            "player",
            "project",
            "created_at",
            "last_updated",
            "is_complete",
            "completed_at",
            "first_completed_at",
            "due_at",
            "parent",
            "subtask_count",
            "total_time",
            "total_records",
            "last_worked_on",
        ]
        read_only_fields = ["player", "first_completed_at"]

    def validate(self, attrs):
        instance = self.instance
        parent = attrs.get("parent", instance.parent if instance else None)

        if instance:
            player_id = instance.player_id
        else:
            request = self.context.get("request")
            player_id = (
                request.user.player.id
                if request and getattr(request.user, "is_authenticated", False)
                else None
            )

        candidate = Task(
            id=instance.id if instance else None,
            player_id=player_id,
            parent=parent,
        )
        try:
            candidate.clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict)
        return attrs


class NoteSerializer(serializers.ModelSerializer):
    player: serializers.PrimaryKeyRelatedField[Player] = (
        serializers.PrimaryKeyRelatedField(read_only=True)
    )

    class Meta:
        model = Note
        fields = [
            "id",
            "title",
            "body",
            "player",
            "task",
            "activity",
            "created_at",
            "last_updated",
        ]
        read_only_fields = ["player"]

    def validate_title(self, value: str) -> str:
        return strip_tags(value).strip()

    def validate_body(self, value: str) -> str:
        return strip_tags(value).strip()

    def validate_task(self, task: Task | None) -> Task | None:
        if task is None:
            return None
        request = self.context.get("request")
        player = getattr(getattr(request, "user", None), "player", None)
        if player is None or task.player_id != player.id:
            raise serializers.ValidationError(
                "Task must belong to the requesting player."
            )
        existing = Note.objects.filter(task=task)
        if self.instance is not None:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise serializers.ValidationError(
                "This task is already linked to another note."
            )
        return task

    def validate_activity(self, activity: Activity | None) -> Activity | None:
        if activity is None:
            return None
        request = self.context.get("request")
        player = getattr(getattr(request, "user", None), "player", None)
        if player is None or activity.player_id != player.id:
            raise serializers.ValidationError(
                "Activity must belong to the requesting player."
            )
        existing = Note.objects.filter(activity=activity)
        if self.instance is not None:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise serializers.ValidationError(
                "This activity is already linked to another note."
            )
        return activity
