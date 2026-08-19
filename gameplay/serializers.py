from rest_framework import serializers

from .models import (
    ActivityTimer,
    XpModifier,
)

from progression.serializers import PlayerActivitySerializer


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
            # The session's declared duration, so the client stops
            # reconstructing it from is_premium and losing it on reload.
            "limit_seconds",
            "limit_reason",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "last_updated",
            "player",
        ]

    def get_elapsed_time(self, obj) -> float:
        return obj.get_elapsed_time()


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
