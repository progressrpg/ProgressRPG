from rest_framework import serializers

from .models import (
    Quest,
    QuestResults,
    QuestRequirement,
    ActivityTimer,
    QuestTimer,
    XpModifier,
)

from progression.serializers import PlayerActivitySerializer


class QuestResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestResults
        fields = ["dynamic_rewards", "xp_rate", "coin_reward"]
        read_only_fields = fields


class QuestSerializer(serializers.ModelSerializer):
    results = QuestResultSerializer(read_only=True)

    class Meta:
        model = Quest
        fields = [
            "id",
            "name",
            "description",
            "intro_text",
            "outro_text",
            "duration_choices",
            "stages",
            "results",
        ]
        read_only_fields = fields


class QuestRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestRequirement
        fields = ["prerequisite", "times_required"]


class ActivityTimerSerializer(serializers.ModelSerializer):
    activity = PlayerActivitySerializer(read_only=True)
    elapsed_time = serializers.SerializerMethodField()

    class Meta:
        model = ActivityTimer
        fields = [
            # Base timer fields
            "id",
            "status",
            "elapsed_time",
            "created_at",
            "last_updated",
            # Activity timer specific fields
            "activity",
            "player",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "last_updated",
            "player",
        ]

    def get_elapsed_time(self, obj):
        return obj.get_elapsed_time()


class QuestTimerSerializer(serializers.ModelSerializer):
    quest = QuestSerializer(read_only=True)
    elapsed_time = serializers.SerializerMethodField()
    remaining_time = serializers.SerializerMethodField()

    class Meta:
        model = QuestTimer
        fields = [
            # Base timer fields
            "id",
            "status",
            "elapsed_time",
            "created_at",
            "last_updated",
            # Quest timer specific fields
            "quest",
            "duration",
            "remaining_time",
            "character",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "last_updated",
            "character",
        ]

    def get_elapsed_time(self, obj):
        return obj.get_elapsed_time()

    def get_remaining_time(self, obj):
        return obj.get_remaining_time()


class XpModifierSerializer(serializers.ModelSerializer):
    class Meta:
        model = XpModifier
        fields = [
            "id",
            "scope",
            "key",
            "multiplier",
            "starts_at",
            "ends_at",
            "is_active",
        ]
        read_only_fields = fields
