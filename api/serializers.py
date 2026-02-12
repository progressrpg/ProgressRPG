from django.contrib.sites.shortcuts import get_current_site
from dj_rest_auth.registration.serializers import RegisterSerializer
from rest_framework import serializers
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)

from users.models import UserLogin, Player, InviteCode

from django.contrib.auth import get_user_model

User = get_user_model()

import logging

logger = logging.getLogger("general")


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        return token

    def validate(self, attrs):
        attrs["username"] = attrs.get("email")
        data = super().validate(attrs)

        UserLogin.objects.create(
            user=self.user
        )  # triggers first-login-of-day automatically

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


class Step1Serializer(serializers.ModelSerializer):
    class Meta:
        model = Player
        fields = ["name"]


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
            user.player.invited_by_code = code
            user.player.save()
        except InviteCode.DoesNotExist:
            # Should not happen due to earlier validation, but fail safe
            pass

    def save(self, request):
        user = super().save(request)
        return user
