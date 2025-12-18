# progression/serializers.py

from rest_framework import serializers
from .models import (
    Category,
    Role,
    PlayerSkill,
    CharacterSkill,
    Activity,
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
    profile = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta(GroupBaseSerializer.Meta):
        model = Category
        fields = GroupBaseSerializer.Meta.fields + ["profile"]
        read_only_fields = ["profile"]


class RoleSerializer(GroupBaseSerializer):
    class Meta(GroupBaseSerializer.Meta):
        model = Role
        fields = GroupBaseSerializer.Meta.fields + ["character"]


#########################################
#####      Skill serializers
#########################################


class PlayerSkillSerializer(SkillBaseSerializer):
    profile = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta(SkillBaseSerializer.Meta):
        model = PlayerSkill
        fields = SkillBaseSerializer.Meta.fields + ["profile", "is_private", "category"]
        read_only_fields = ["profile"]


class CharacterSkillSerializer(SkillBaseSerializer):
    class Meta(SkillBaseSerializer.Meta):
        model = CharacterSkill
        fields = SkillBaseSerializer.Meta.fields + ["character", "roles"]


#########################################
#####      TimeRecord serializers
#########################################


class ActivitySerializer(TimeRecordBaseSerializer):
    profile = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta(TimeRecordBaseSerializer.Meta):
        model = Activity
        fields = TimeRecordBaseSerializer.Meta.fields + [
            "profile",
            "is_private",
            "skill",
            "project",
            "task",
        ]
        read_only_fields = ["profile"]


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
    total_time = serializers.IntegerField(read_only=True)
    total_records = serializers.IntegerField(read_only=True)

    class Meta:
        model = Project
        fields = [
            "id",
            "name",
            "description",
            "profile",
            "created_at",
            "last_updated",
            "total_time",
            "total_records",
        ]


class TaskSerializer(serializers.ModelSerializer):
    total_time = serializers.IntegerField(read_only=True)
    total_records = serializers.IntegerField(read_only=True)

    class Meta:
        model = Task
        fields = [
            "id",
            "name",
            "description",
            "profile",
            "project",
            "created_at",
            "last_updated",
            "total_time",
            "total_records",
        ]
