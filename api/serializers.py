from dj_rest_auth.registration.serializers import RegisterSerializer
from django.contrib.sites.shortcuts import get_current_site
from rest_framework import serializers

from character.models import Character, PlayerCharacterLink
from gameplay.models import (
    Quest,
    QuestResults,
    QuestRequirement,
    QuestCompletion,
    Activity,
    ActivityTimer,
    QuestTimer,
)
from users.models import Profile, InviteCode

from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)

from django.contrib.auth import get_user_model

User = get_user_model()

import logging

logger = logging.getLogger("django")


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        return token

    def validate(self, attrs):
        attrs["username"] = attrs.get("email")
        data = super().validate(attrs)

        return {
            "access_token": data["access"],
            "refresh_token": data["refresh"],
        }


class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        return {
            "access_token": data["access"],
        }


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "email",
            "is_confirmed",
            "is_staff",
            "is_superuser",
            "date_of_birth",
        ]


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
            "login_streak",
        ]
        read_only_fields = [
            "id",
        ]


class Step1Serializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ["name"]


class Step2Serializer(serializers.Serializer):
    # No extra fields for linking character, just confirmation
    confirm_link = serializers.BooleanField()


class Step3Serializer(serializers.Serializer):
    # No extra data, just confirming tutorial completion
    confirm_tutorial = serializers.BooleanField()


class CharacterSerializer(serializers.ModelSerializer):
    population_centre_id = serializers.PrimaryKeyRelatedField(
        source="population_centre", read_only=True
    )
    location = serializers.SerializerMethodField()  # use method

    class Meta:
        model = Character
        fields = [
            "id",
            "first_name",
            "last_name",
            "backstory",
            "sex",
            "xp",
            "xp_next_level",
            "xp_modifier",
            "level",
            "coins",
            "total_quests",
            "is_npc",
            "can_link",
            "population_centre_id",
            "location",
        ]
        read_only_fields = [
            "id",
        ]

    def get_location(self, obj):
        # obj must have x and y attributes, or replace with obj.position.x / obj.position.y
        return {
            "type": "Point",
            "coordinates": [obj.location.x, obj.location.y],  # adjust to your model
        }


class QuestRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestRequirement
        fields = ["prerequisite", "times_required"]


class QuestCompletionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestCompletion
        fields = ["character", "quest", "times_completed", "last_completed"]


class QuestResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestResults
        fields = ["dynamic_rewards", "xp_rate", "coin_reward"]


class ActivitySerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    last_updated = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = Activity
        fields = [
            "id",
            "name",
            "duration",
            "created_at",
            "last_updated",
            "completed_at",
            "profile",
            "skill",
            "project",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "last_updated",
            "completed_at",
            "profile",
        ]


class QuestSerializer(serializers.ModelSerializer):
    results = QuestResultSerializer(read_only=True)  # source='results',

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
            "stagesFixed",
            "results",
        ]
        read_only_fields = [
            "id",
        ]


class ActivityTimerSerializer(serializers.ModelSerializer):
    activity = ActivitySerializer(read_only=True)
    # logger.debug(f"API Activity serializer: {activity}")
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
            "profile",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "last_updated",
            "profile",
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


class CustomRegisterSerializer(RegisterSerializer):
    invite_code = serializers.CharField(write_only=True, required=True)
    agree_to_terms = serializers.BooleanField(write_only=True, required=True)
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ("email", "password1", "password2", "invite_code", "agree_to_terms")

    def get_email_context(self):
        context = super().get_email_context()
        request = self.context.get("request")
        if request:
            current_site = get_current_site(request)
            context["domain"] = current_site.domain
            context["protocol"] = "https" if request.is_secure() else "http"
        return context

    def validate_invite_code(self, value):
        try:
            invite = InviteCode.objects.get(code=value, is_active=True)
        except InviteCode.DoesNotExist:
            raise serializers.ValidationError("Invalid or expired invite code.")
        return value

    def validate_agree_to_terms(self, value):
        if not value:
            raise serializers.ValidationError(
                "You must agree to the terms and conditions."
            )
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with that email already exists.")
        return value

    def custom_signup(self, request, user):
        code = self.validated_data.get("invite_code")
        try:
            invite = InviteCode.objects.get(code=code, is_active=True)
            invite.use()
            user.profile.invited_by_code = code
            user.profile.save()
        except InviteCode.DoesNotExist:
            # Should not happen due to earlier validation, but fail safe
            pass

    def save(self, request):
        user = super().save(request)
        return user


class ObjectLocationSerializer(serializers.Serializer):
    x = serializers.FloatField()
    y = serializers.FloatField()

    def to_representation(self, obj):
        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [obj.location.x, obj.location.y],
            },
            "properties": {
                "id": obj.id,
                "name": getattr(obj, "name", ""),
            },
        }


class PolygonFeatureSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    coords = serializers.SerializerMethodField()
    name = serializers.CharField()

    def get_coords(self, obj):
        # Returns list of linear rings
        # obj.footprint.coords gives outer ring only unless you use holes
        outer_ring = obj.footprint.coords[0]
        return [[list(map(float, point)) for point in outer_ring]]

    def to_representation(self, obj):
        rep = super().to_representation(obj)
        coords = rep.pop("coords")

        return {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": coords},
            "properties": rep,
        }


class BoundaryFeatureSerializer(serializers.Serializer):
    coords = serializers.SerializerMethodField()

    def get_coords(self, obj):
        outer_ring = obj.boundary.coords[0]
        return [[list(map(float, point)) for point in outer_ring]]

    def to_representation(self, obj):
        coords = self.get_coords(obj)
        return {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": coords},
            "properties": {"type": "boundary"},
        }
