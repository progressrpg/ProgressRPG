from rest_framework import serializers

from .achievements import achievement_goals_for_player
from .models import Player, TutorialStep
from .validators import clean_player_name


class TutorialStepSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    alt_text = serializers.SerializerMethodField()

    def get_image_url(self, obj):
        if not obj.image:
            return None
        request = self.context.get("request")
        url = obj.image.image.url
        return request.build_absolute_uri(url) if request else url

    def get_alt_text(self, obj):
        return obj.image.alt_text if obj.image else ""

    class Meta:
        model = TutorialStep
        fields = [
            "id",
            "order",
            "title",
            "body",
            "image_url",
            "alt_text",
            "youtube_url",
        ]


class PlayerSerializer(serializers.ModelSerializer):
    total_time = serializers.IntegerField(read_only=True)
    total_activities = serializers.IntegerField(read_only=True)
    achievements = serializers.SerializerMethodField()
    is_premium = serializers.BooleanField(source="user.is_premium", read_only=True)
    has_previous_subscription = serializers.BooleanField(
        source="user.has_previous_subscription", read_only=True
    )
    login_streak = serializers.IntegerField(
        source="user.current_login_streak", read_only=True
    )
    unseen_tutorial_step_ids = serializers.SerializerMethodField()

    def get_unseen_tutorial_step_ids(self, obj):
        seen_ids = set(obj.tutorial_steps_seen.values_list("id", flat=True))
        all_ids = set(TutorialStep.objects.values_list("id", flat=True))
        return sorted(all_ids - seen_ids)

    def get_achievements(self, obj):
        return achievement_goals_for_player(obj)

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
            "achievements",
            "is_premium",
            "has_previous_subscription",
            "onboarding_step",
            "onboarding_completed",
            "login_streak",
            "unseen_tutorial_step_ids",
        ]
        read_only_fields = [
            "id",
            "xp",
            "xp_next_level",
            "xp_modifier",
            "level",
            "total_time",
            "total_activities",
            "achievements",
            "is_premium",
            "has_previous_subscription",
            "login_streak",
            "unseen_tutorial_step_ids",
        ]
