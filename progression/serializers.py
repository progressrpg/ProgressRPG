# progression/serializers.py

from django.utils import timezone
from rest_framework import serializers

from .models import (
    Category,
    Role,
    PlayerSkill,
    CharacterSkill,
    PlayerActivity,
    CharacterActivity,
    CharacterQuest,
    Project,
    Task,
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
            "created_at",
            "last_updated",
        ]
        abstract = True


#########################################
#####      Group serializers
#########################################


class CategorySerializer(GroupBaseSerializer):
    player = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta(GroupBaseSerializer.Meta):
        model = Category
        fields = GroupBaseSerializer.Meta.fields + ["player"]
        read_only_fields = ["player"]


class RoleSerializer(GroupBaseSerializer):
    class Meta(GroupBaseSerializer.Meta):
        model = Role
        fields = GroupBaseSerializer.Meta.fields + ["character"]


#########################################
#####      Skill serializers
#########################################


class PlayerSkillSerializer(SkillBaseSerializer):
    player = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta(SkillBaseSerializer.Meta):
        model = PlayerSkill
        fields = SkillBaseSerializer.Meta.fields + ["player", "is_private", "category"]
        read_only_fields = ["player"]


class CharacterSkillSerializer(SkillBaseSerializer):
    class Meta(SkillBaseSerializer.Meta):
        model = CharacterSkill
        fields = SkillBaseSerializer.Meta.fields + ["character", "roles"]


#########################################
#####      TimeRecord serializers
#########################################


class PlayerActivitySerializer(TimeRecordBaseSerializer):
    player = serializers.PrimaryKeyRelatedField(read_only=True)
    group_key = serializers.CharField(read_only=True)

    class Meta(TimeRecordBaseSerializer.Meta):
        model = PlayerActivity
        fields = TimeRecordBaseSerializer.Meta.fields + [
            "player",
            "group_key",
            "is_private",
            "skill",
            "project",
            "task",
        ]
        read_only_fields = ["player"]


class CharacterActivitySerializer(TimeRecordBaseSerializer):
    status = serializers.SerializerMethodField()

    class Meta(TimeRecordBaseSerializer.Meta):
        model = CharacterActivity
        fields = TimeRecordBaseSerializer.Meta.fields + [
            "character",
            "scheduled_start",
            "scheduled_end",
            "status",
            "kind",
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


class CharacterQuestSerializer(TimeRecordBaseSerializer):
    class Meta(TimeRecordBaseSerializer.Meta):
        model = CharacterQuest
        fields = TimeRecordBaseSerializer.Meta.fields + [
            "character",
            "skill",
            "intro_text",
            "outro_text",
            "target_duration",
            "stages",
            "stages_fixed",
        ]


#########################################
#####      Other serializers
#########################################


class ProjectSerializer(serializers.ModelSerializer):
    player = serializers.PrimaryKeyRelatedField(read_only=True)
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
    player = serializers.PrimaryKeyRelatedField(read_only=True)
    total_time = serializers.IntegerField(read_only=True)
    total_records = serializers.IntegerField(read_only=True)

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
            "total_time",
            "total_records",
        ]
        read_only_fields = ["player"]
