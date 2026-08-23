from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field

from .achievements import achievement_goals_for_player
from .models import Player, TutorialStep
from .services import progressive_unlocks
from .validators import clean_player_name


class AchievementGoalSerializer(serializers.Serializer):
    type = serializers.CharField()  # type: ignore[assignment]
    label = serializers.CharField()  # type: ignore[assignment]
    symbol = serializers.CharField()
    tier = serializers.IntegerField()
    complete = serializers.BooleanField()
    color = serializers.CharField()
    value = serializers.IntegerField()
    threshold = serializers.IntegerField()
    next_threshold = serializers.IntegerField(allow_null=True)


class TutorialStepSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    alt_text = serializers.SerializerMethodField()

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_image_url(self, obj) -> str | None:
        if not obj.image:
            return None
        request = self.context.get("request")
        url = obj.image.image.url
        return request.build_absolute_uri(url) if request else url

    @extend_schema_field(OpenApiTypes.STR)
    def get_alt_text(self, obj) -> str:
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
    is_tester = serializers.SerializerMethodField()
    has_previous_subscription = serializers.BooleanField(
        source="user.has_previous_subscription", read_only=True
    )
    is_trialing = serializers.BooleanField(source="user.is_trialing", read_only=True)
    trial_end = serializers.DateTimeField(source="user.trial_end", read_only=True)
    login_streak = serializers.IntegerField(
        source="user.current_login_streak", read_only=True
    )
    unseen_tutorial_step_ids = serializers.SerializerMethodField()
    progressive_unlocks = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_is_tester(self, obj) -> bool:
        return obj.user.groups.filter(name="Testers").exists()

    @extend_schema_field(serializers.ListField(child=serializers.IntegerField()))
    def get_unseen_tutorial_step_ids(self, obj) -> list[int]:
        seen_ids = set(obj.tutorial_steps_seen.values_list("id", flat=True))
        eligible_ids = set(
            TutorialStep.objects.exclude(unlock_key="").values_list("id", "unlock_key")
        )
        gated_ids = {
            step_id
            for step_id, unlock_key in eligible_ids
            if not progressive_unlocks.new_signup_milestone_reached(obj, unlock_key)
        }
        all_ids = set(TutorialStep.objects.values_list("id", flat=True))
        return sorted(all_ids - seen_ids - gated_ids)

    @extend_schema_field(serializers.DictField(child=serializers.BooleanField()))
    def get_progressive_unlocks(self, obj) -> dict[str, bool]:
        return {
            key: progressive_unlocks.unlock_visible(obj, key)
            for key in (
                progressive_unlocks.INFOBAR,
                progressive_unlocks.LIBRARY,
                progressive_unlocks.MAP,
            )
        }

    @extend_schema_field(AchievementGoalSerializer(many=True))
    def get_achievements(self, obj) -> list[dict[str, object]]:
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
            "is_tester",
            "has_previous_subscription",
            "is_trialing",
            "trial_end",
            "onboarding_step",
            "onboarding_completed",
            "login_streak",
            "unseen_tutorial_step_ids",
            "progressive_unlocks",
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
            "is_tester",
            "has_previous_subscription",
            "is_trialing",
            "trial_end",
            "login_streak",
            "unseen_tutorial_step_ids",
            "progressive_unlocks",
        ]
