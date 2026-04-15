from rest_framework import serializers

from .models import Player
from .validators import clean_player_name


class PlayerSerializer(serializers.ModelSerializer):
    total_time = serializers.IntegerField(read_only=True)
    total_activities = serializers.IntegerField(read_only=True)
    is_premium = serializers.BooleanField(source="user.is_premium", read_only=True)
    login_streak = serializers.IntegerField(
        source="user.current_login_streak", read_only=True
    )

    def validate_name(self, value):
        try:
            return clean_player_name(value)
        except ValueError as exc:
            raise serializers.ValidationError("Invalid player name.") from exc

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
