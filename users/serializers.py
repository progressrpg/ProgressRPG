from rest_framework import serializers

from .models import Player


class PlayerSerializer(serializers.ModelSerializer):
    total_time = serializers.IntegerField(read_only=True)
    total_activities = serializers.IntegerField(read_only=True)
    login_streak = serializers.IntegerField(
        source="user.current_login_streak", read_only=True
    )

    class Meta:
        model = Player
        fields = [
            "id",
            "name",
            "xp",
            "xp_next_level",
            "xp_modifier",
            "level",
            "total_time",
            "total_activities",
            "is_premium",
            "onboarding_step",
            "onboarding_completed",
            "login_streak",
        ]
        read_only_fields = [
            "id",
            "xp",
            "xp_next_level",
            "xp_modifier",
            "level",
            "total_time",
            "total_activities",
            "login_streak",
        ]
