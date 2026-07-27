import requests as http_requests
from typing import Any, cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from dj_rest_auth.registration.serializers import RegisterSerializer
from dj_rest_auth.serializers import PasswordResetSerializer
from rest_framework import serializers
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)
from rest_framework_simplejwt.tokens import RefreshToken, Token

from core.models import Announcement, GameSettings
from users.models import Player, InviteCode, UserLogin, Waitlist
from users.services.registration_services import (
    ensure_player_setup_for_user,
    verified_user_count,
)
from users.validators import clean_player_name, reject_disposable_email

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
    remember_me = serializers.BooleanField(
        required=False, default=False, write_only=True
    )

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        return token

    def validate(self, attrs):
        remember_me = attrs.pop("remember_me", False)
        attrs["username"] = attrs.get("email")

        data = super().validate(attrs)
        assert self.user is not None
        UserLogin.objects.create(user=self.user)

        if remember_me:
            refresh_token = data.get("refresh")
            if not isinstance(refresh_token, str):
                raise serializers.ValidationError("Invalid refresh token payload.")
            # SimpleJWT accepts encoded token strings at runtime, but stubs type this as Token|None.
            refresh = RefreshToken(cast(Token, refresh_token))
            refresh.set_exp(lifetime=settings.LONG_SESSION_REFRESH_TOKEN_LIFETIME)
            data["refresh"] = str(refresh)
            data["access"] = str(refresh.access_token)

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
    announcement_unread_count = serializers.IntegerField()
    free_timer_limit_seconds = serializers.IntegerField()
    game_settings = serializers.JSONField()
    online_count = serializers.IntegerField()


class AnnouncementSerializer(serializers.ModelSerializer):
    is_read = serializers.SerializerMethodField()

    def get_is_read(self, obj) -> bool:
        read_ids = self.context.get("read_ids", set())
        return obj.id in read_ids

    class Meta:
        model = Announcement
        fields = [
            "id",
            "title",
            "summary",
            "body",
            "published_at",
            "created_at",
            "is_read",
        ]


class AnnouncementListResponseSerializer(serializers.Serializer):
    unread_count = serializers.IntegerField()
    results = AnnouncementSerializer(many=True)


class AnnouncementUnreadCountSerializer(serializers.Serializer):
    unread_count = serializers.IntegerField()


class MarkAnnouncementReadRequestSerializer(serializers.Serializer):
    announcement_id = serializers.IntegerField()


class MarkAnnouncementReadResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    unread_count = serializers.IntegerField()


class MarkAllAnnouncementsReadResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    unread_count = serializers.IntegerField()


class GameSettingsSerializer(serializers.Serializer):
    free_timer_limit_seconds = serializers.IntegerField()
    daily_login_base_xp = serializers.IntegerField()
    daily_login_streak_step_xp = serializers.IntegerField()
    daily_login_max_xp = serializers.IntegerField()
    premium_activity_xp_multiplier = serializers.DecimalField(
        max_digits=5, decimal_places=2
    )
    default_activity_xp_per_second = serializers.DecimalField(
        max_digits=5, decimal_places=4
    )
    activity_search_includes_tasks = serializers.BooleanField()


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

    def validate_email(self, value):
        try:
            reject_disposable_email(value)
        except ValueError as exc:
            raise serializers.ValidationError(
                "Please use a valid non-disposable email address."
            ) from exc
        return value


class WaitlistSignupResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    state = serializers.ChoiceField(choices=["pending", "subscribed"])


class RegistrationStatusResponseSerializer(serializers.Serializer):
    registration_open = serializers.BooleanField()
    registration_enabled = serializers.BooleanField()
    self_serve_registration = serializers.BooleanField()
    waitlist_signup_provider = serializers.ChoiceField(choices=["mailchimp", "internal"])
    turnstile_site_key = serializers.CharField(allow_blank=True)


class WaitlistJoinRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        try:
            reject_disposable_email(value)
        except ValueError as exc:
            raise serializers.ValidationError(
                "Please use a valid non-disposable email address."
            ) from exc
        return value


class WaitlistJoinResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


def _frontend_password_reset_url(request, user, temp_key):
    from allauth.account.utils import user_pk_to_url_str

    uid = user_pk_to_url_str(user)
    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")
    return f"{frontend_url}/reset-password/{uid}-{temp_key}"


class CustomPasswordResetSerializer(PasswordResetSerializer):
    def get_email_options(self):
        return {"url_generator": _frontend_password_reset_url}


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
    invite_code = serializers.CharField(
        write_only=True, required=False, allow_blank=True
    )
    invite_token = serializers.CharField(
        write_only=True, required=False, allow_blank=True
    )
    agree_to_terms = serializers.BooleanField(write_only=True, required=True)
    # Blank is allowed so deployments without a Turnstile site key (local dev,
    # tests) can still register; verification below rejects a blank token
    # whenever a secret *is* configured.
    turnstile_token = serializers.CharField(
        write_only=True, required=True, allow_blank=True
    )
    email = serializers.EmailField(required=True)
    timezone = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = (
            "email",
            "password1",
            "password2",
            "invite_code",
            "invite_token",
            "agree_to_terms",
            "turnstile_token",
            "timezone",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The inherited RegisterSerializer may expose a username field even
        # when the project has no username field, yielding impossible
        # validation constraints (required with max_length=0).
        self.fields.pop("username", None)

    def get_email_context(self):
        context: dict[str, Any] = {}
        base_get_email_context = getattr(super(), "get_email_context", None)
        if callable(base_get_email_context):
            base_context = base_get_email_context()
            if isinstance(base_context, dict):
                context.update(base_context)
        request = self.context.get("request")
        if request:
            current_site = get_current_site(request)
            context["domain"] = current_site.domain
            context["protocol"] = "https" if request.is_secure() else "http"
        return context

    def validate_invite_code(self, value):
        if not value:
            return value
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
        try:
            reject_disposable_email(value)
        except ValueError as exc:
            raise serializers.ValidationError(
                "Please use a valid non-disposable email address."
            ) from exc
        return value

    def validate_timezone(self, value):
        return validate_timezone_name(value)

    def validate(self, data):
        data = super().validate(data)
        invite_code = data.get("invite_code")
        invite_token = data.get("invite_token")
        if invite_code and invite_token:
            raise serializers.ValidationError(
                "Provide at most one of invite_code or invite_token."
            )
        if not invite_code and not invite_token:
            game_settings = GameSettings.current()
            if not game_settings.self_serve_registration:
                raise serializers.ValidationError(
                    "Provide exactly one of invite_code or invite_token."
                )
            # Self-serve signups must respect the cap; invite holders bypass
            # it because their invite is proof of a slot at invite time.
            # Only confirmed users count, so unconfirmed/abandoned signups
            # can't exhaust the cap and block real users.
            if verified_user_count() >= game_settings.registration_cap:
                raise serializers.ValidationError(
                    "Registration is currently full. Please join the waitlist."
                )
        if invite_token:
            try:
                entry = Waitlist.objects.get(
                    invite_token=invite_token, status=Waitlist.Status.INVITED
                )
            except Waitlist.DoesNotExist:
                raise serializers.ValidationError(
                    {"invite_token": "Invalid or already used invite token."}
                )
            if entry.email != data.get("email", "").strip().lower():
                raise serializers.ValidationError(
                    {
                        "invite_token": "This invite token is for a different email address."
                    }
                )
            self._waitlist_entry = entry
        return data

    def custom_signup(self, request, user):
        ensure_player_setup_for_user(user)
        invite_code = self.validated_data.get("invite_code")
        if invite_code:
            try:
                invite = InviteCode.objects.get(code=invite_code)
                if not invite.use():
                    raise serializers.ValidationError("Invalid or expired invite code.")
            except InviteCode.DoesNotExist:
                # Should not happen due to earlier validation, but fail safe
                raise serializers.ValidationError("Invalid or expired invite code.")
        elif self.validated_data.get("invite_token"):
            entry = self._waitlist_entry
            updated = Waitlist.objects.filter(
                pk=entry.pk, status=Waitlist.Status.INVITED
            ).update(status=Waitlist.Status.REDEEMED)
            if not updated:
                raise serializers.ValidationError(
                    {"invite_token": "This invite token has already been redeemed."}
                )

    def save(self, request):
        user = super().save(request)
        timezone_name = self.validated_data.get("timezone")
        if isinstance(timezone_name, str) and timezone_name:
            if not hasattr(user, "timezone"):
                raise serializers.ValidationError(
                    "User model does not support timezone."
                )
            setattr(user, "timezone", timezone_name)
            user.save(update_fields=["timezone"])
        return user
