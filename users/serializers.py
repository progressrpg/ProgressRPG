from rest_framework import serializers

from .models import Profile


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
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
