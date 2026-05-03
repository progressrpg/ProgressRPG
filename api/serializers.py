import requests as http_requests
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from dj_rest_auth.registration.serializers import RegisterSerializer
from rest_framework import serializers
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)

from users.models import Player, InviteCode, UserLogin
from users.validators import clean_player_name

from django.contrib.auth import get_user_model

User = get_user_model()

import logging

logger = logging.getLogger("general")


def validate_timezone_name(value: str) -> str:
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise serializers.ValidationError("Invalid timezone.") from exc
    return value


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        return token

    def validate(self, attrs):
        attrs["username"] = attrs.get("email")
        data = super().validate(attrs)
        UserLogin.objects.create(user=self.user)

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
    timezone = serializers.CharField()

    class Meta:
        model = User
        fields = [
            "email",
            "is_confirmed",
            "is_staff",
            "is_superuser",
            "date_of_birth",
            "timezone",
        ]


class UserSettingsSerializer(serializers.ModelSerializer):
    timezone = serializers.CharField(required=False)

    class Meta:
        model = User
        fields = ["timezone"]

    def validate_timezone(self, value):
        return validate_timezone_name(value)


class Step1Serializer(serializers.ModelSerializer):
    def validate_name(self, value):
        try:
            return clean_player_name(value)
        except ValueError as exc:
            logger.warning("Invalid player name provided: %s", exc)
            raise serializers.ValidationError("Invalid player name.") from exc

    class Meta:
        model = Player
        fields = ["name"]


class ConfirmEmailResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    access = serializers.CharField()
    refresh = serializers.CharField()


class ConfirmEmailAlreadyConfirmedSerializer(serializers.Serializer):
    message = serializers.CharField()
    code = serializers.CharField()


class FetchInfoResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    build_number = serializers.CharField()
    player = serializers.JSONField()
    character = serializers.JSONField()
    activity_timer = serializers.JSONField()
    population_centre = serializers.JSONField(allow_null=True)
    xp_mods = serializers.ListField(child=serializers.JSONField())
    login_state = serializers.CharField()
    login_streak = serializers.IntegerField()
    login_event_at = serializers.DateTimeField(allow_null=True)
    login_reward_xp = serializers.IntegerField()


class DownloadUserDataPlayerSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    player_name = serializers.CharField()
    level = serializers.IntegerField()
    xp = serializers.IntegerField()
    bio = serializers.CharField(allow_blank=True, allow_null=True)
    total_time = serializers.IntegerField()
    total_activities = serializers.IntegerField()
    is_premium = serializers.BooleanField()


class DownloadUserDataCharacterSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    character_name = serializers.CharField()
    level = serializers.IntegerField()
    total_activities = serializers.IntegerField()


class DownloadUserDataResponseSerializer(serializers.Serializer):
    email = serializers.EmailField()
    player = DownloadUserDataPlayerSerializer()
    activities = serializers.ListField(child=serializers.JSONField())
    character = DownloadUserDataCharacterSerializer()


class DeleteAccountResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


class WaitlistSignupRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


class WaitlistSignupResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    state = serializers.ChoiceField(choices=["pending", "subscribed"])


def _verify_turnstile(token: str) -> bool:
    secret = getattr(settings, "CF_TURNSTILE_SECRET_KEY", "")
    if not secret:
        # No secret configured — skip verification (e.g. local dev without key)
        return True
    try:
        resp = http_requests.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={"secret": secret, "response": token},
            timeout=5,
        )
        return resp.json().get("success", False)
    except Exception:
        return False


class CustomRegisterSerializer(RegisterSerializer):
    invite_code = serializers.CharField(write_only=True, required=True)
    agree_to_terms = serializers.BooleanField(write_only=True, required=True)
    turnstile_token = serializers.CharField(write_only=True, required=True)
    email = serializers.EmailField(required=True)
    timezone = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = (
            "email",
            "password1",
            "password2",
            "invite_code",
            "agree_to_terms",
            "turnstile_token",
            "timezone",
        )

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

    def validate_turnstile_token(self, value):
        if not _verify_turnstile(value):
            raise serializers.ValidationError(
                "Security check failed. Please refresh and try again."
            )
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with that email already exists.")
        return value

    def validate_timezone(self, value):
        return validate_timezone_name(value)

    def custom_signup(self, request, user):
        code = self.validated_data.get("invite_code")
        try:
            invite = InviteCode.objects.get(code=code, is_active=True)
            invite.use()
            user.player.invited_by_code = code
            user.player.save()
        except InviteCode.DoesNotExist:
            # Should not happen due to earlier validation, but fail safe
            pass

    def save(self, request):
        user = super().save(request)
        timezone_name = self.validated_data.get("timezone")
        if timezone_name:
            user.timezone = timezone_name
            user.save(update_fields=["timezone"])
        return user
