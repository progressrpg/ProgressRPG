from rest_framework import serializers

from .models import CustomUser as User, Player


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "email",
            "is_confirmed",
            "is_staff",
            "is_superuser",
            "date_of_birth",
            "created_at",
            "last_login",
            "days_logged_in",
            "current_login_streak",
            "max_login_streak",
        ]
        read_only_fields = fields


class PlayerSerializer(serializers.ModelSerializer):
    total_time = serializers.IntegerField(read_only=True)
    total_activities = serializers.IntegerField(read_only=True)

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
        ]
        read_only_fields = [
            "id",
            "xp",
            "xp_next_level",
            "xp_modifier",
            "level",
            "total_time",
            "total_activities",
        ]
