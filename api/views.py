# api/views.py
from asgiref.sync import async_to_sync

# from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth import login, logout, get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.db import DatabaseError, transaction
from django.http import Http404

from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.html import escape
from django.views.decorators.csrf import csrf_exempt
from django_filters.rest_framework import DjangoFilterBackend
from django_ratelimit.decorators import ratelimit
from urllib.parse import quote, unquote

from allauth.account import app_settings as allauth_settings
from allauth.account.models import EmailConfirmation, EmailAddress

# from allauth.account.utils import complete_signup, send_email_confirmation
from dj_rest_auth.registration.views import RegisterView

from rest_framework import viewsets, permissions, serializers, status, mixins
from rest_framework.decorators import (
    api_view,
    permission_classes,
    action,
    authentication_classes,
)
from rest_framework.exceptions import ValidationError

# from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

# from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from api.serializers import (
    UserSerializer,
    Step1Serializer,
    # Step2Serializer,
    # Step3Serializer,
    CustomRegisterSerializer,
    CustomTokenObtainPairSerializer,
    CustomTokenRefreshSerializer,
)

from character.models import Character, PlayerCharacterLink
from character.serializers import CharacterSerializer

from gameplay.models import Quest, ServerMessage
from gameplay.utils import send_group_message
from gameplay.serializers import (
    QuestSerializer,
    ActivityTimerSerializer,
    QuestTimerSerializer,
)

from progression.models import Activity, Task
from progression.serializers import ActivitySerializer
from progression.utils import copy_quest

from users.models import Profile
from users.serializers import ProfileSerializer
from users.utils import send_email_to_users

from progress_rpg.settings.utils import get_build_number

import logging

logger = logging.getLogger("django")


class IsOwnerProfile(permissions.BasePermission):
    owner_attr = "profile"

    def has_object_permission(self, request, view, obj):
        profile = getattr(request.user, "profile", None)
        if profile is None:
            return False

        # Check if object has 'profile' attribute and compare
        if hasattr(obj, "profile"):
            return obj.profile == profile

        return False


class IsOwnerCharacter(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        profile = getattr(request.user, "profile", None)
        if profile is None:
            return False

        # Check if the object's character is linked to the profile and active
        if hasattr(obj, "character"):
            return PlayerCharacterLink.objects.filter(
                profile=profile, character=obj.character, is_active=True
            ).exists()

        return False


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    @csrf_exempt
    @api_view(["POST"])
    def test_post_view(request):
        permission_classes = [IsAuthenticated]
        return Response(
            {"status": "ok", "message": f"Hello {request.user.email}! POST successful!"}
        )


class CustomTokenRefreshView(TokenRefreshView):
    serializer_class = CustomTokenRefreshSerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_view(request):
    user = request.user
    serializer = UserSerializer(user)
    return Response({"success": True, "user": serializer.data})


class CustomRegisterView(RegisterView):
    serializer_class = CustomRegisterSerializer

    def perform_create(self, serializer):
        user = serializer.save(self.request)

        backend_path = settings.AUTHENTICATION_BACKENDS[0]
        user.backend = backend_path

        email_address, created = EmailAddress.objects.get_or_create(
            user=user,
            email=user.email,
            defaults={"verified": False, "primary": True},
        )

        email_address.save()

        logger.debug(f"[REGISTER] EmailAddress: {email_address} (created={created})")

        confirmation = EmailConfirmation.create(email_address)
        confirmation.sent = timezone.now()
        confirmation.save()

        quoted_key = quote(confirmation.key)
        activate_url = f"{settings.FRONTEND_URL}/confirm_email/{quoted_key}"

        context = {
            "user": {
                "email": user.email,
                "first_name": user.first_name,
            },
            "activate_url": activate_url,
        }

        send_email_to_users(
            users=[user],
            subject="Confirm your Progress RPG email",
            template_base="emails/email_confirmation_message",
            context=context,
            cc_admin=False,
        )

        """
        if confirmation:

            logger.debug(f"[REGISTER] Sent confirmation to: {user.email}")
            logger.debug(f"[REGISTER] EmailConfirmation key: {confirmation.key}")
            logger.debug(f"[REGISTER] Quoted key: {quoted_key}")
            logger.debug(f"[REGISTER] Confirmation URL: {activate_url}")
        else:
            logger.warning(f"[REGISTER] No EmailConfirmation found for {user.email}")
        """
        return user

    def get_response_data(self, user):
        available_character = Character.has_available()

        return {
            "needs_confirmation": True,
            "detail": "Registration successful. Please confirm your email to activate your account.",
            "characters_available": available_character,
        }


class ConfirmEmailView(APIView):
    permission_classes = []  # No auth required for email confirmation

    def get(self, request, key):
        key = unquote(key)

        try:
            confirmation = EmailConfirmation.objects.get(key=key)
            email_address = confirmation.email_address

            if email_address.verified:
                return Response(
                    {
                        "message": "Email already confirmed",
                        "code": "already_confirmed",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            confirmation.confirm(request)

            user = email_address.user

            """
            # Optional: set custom user field if you're tracking confirmation manually
            if hasattr(user, 'is_confirmed'):
                user.is_confirmed = True
                user.save() """

            # Create JWT tokens
            refresh = RefreshToken.for_user(user)
            access = str(refresh.access_token)

            return Response(
                {
                    "message": "Email confirmed",
                    "access": access,
                    "refresh": str(refresh),
                },
                status=status.HTTP_200_OK,
            )
        except EmailConfirmation.DoesNotExist:
            logger.info(f"Confirmation object not found for key: {key}")
            raise Http404("Invalid or expired confirmation key")
        except Exception as e:
            logger.warning(f"Unexpected error: {str(e)}")
            raise Http404("Something went wrong")


class OnboardingViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def get_profile(self, request):
        return request.user.profile

    @action(detail=False, methods=["get"])
    def status(self, request):
        profile = self.get_profile(request)
        if profile.onboarding_step == 0:
            profile.onboarding_step = 1
            profile.save()
        return Response(
            {
                "step": request.user.profile.onboarding_step,
                "characters_available": Character.has_available(),
            }
        )

    @action(detail=False, methods=["post"])
    def progress(self, request):
        profile = self.get_profile(request)
        step = profile.onboarding_step

        handlers = {
            1: self.handle_step1,
            2: self.handle_step2,
            3: self.handle_step3,
        }

        handler = handlers.get(step)
        if handler:
            return handler(profile, request)
        return Response({"message": "Onboarding complete."}, status=200)

    def handle_step1(self, profile, request):
        serializer = Step1Serializer(profile, data=request.data, partial=True)
        characters_available = Character.has_available()
        character = PlayerCharacterLink.get_character(profile)
        if character is not None:
            character_data = CharacterSerializer(
                character, context={"request": request}
            ).data
        if serializer.is_valid():
            serializer.save()
            profile.onboarding_step = 2
            profile.save()
            return Response(
                {
                    "message": "Step 1 complete.",
                    "step": profile.onboarding_step,
                    "characters_available": characters_available,
                    "character": character_data if character else None,
                }
            )
        return Response(serializer.errors, status=400)

    def handle_step2(self, profile, request):
        character = PlayerCharacterLink.get_character(profile)
        if not character:
            return Response({"error": "No active character link found."}, status=404)

        profile.onboarding_step = 3
        profile.save()
        character_data = CharacterSerializer(
            character, context={"request": request}
        ).data
        return Response(
            {
                "message": "Step 2 complete.",
                "step": profile.onboarding_step,
                "character": character_data,
            }
        )

    def handle_step3(self, profile, request):
        profile.onboarding_step = 4
        profile.save()
        return Response(
            {
                "message": "Stage 3 complete. Onboarding finished!",
                "step": profile.onboarding_step,
            }
        )


class FetchInfoAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        profile = request.user.profile
        build_number = get_build_number()

        try:
            character = PlayerCharacterLink.get_character(profile)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        logger.info(
            f"[FETCH INFO] Fetching data for profile {profile.id}, character {character.id}"
        )

        # --- Auto-complete quest timer if expired ---
        self._handle_quest_timer_expiry(character, profile)

        # --- Ensure activity timer is in a valid state ---
        self._ensure_activity_timer_consistency(profile)

        # --- Serialize everything ---
        try:
            data = {
                "success": True,
                "message": "Profile and character fetched",
                "build_number": build_number,
                "profile": ProfileSerializer(
                    profile, context={"request": request}
                ).data,
                "character": CharacterSerializer(
                    character, context={"request": request}
                ).data,
                "activity_timer": ActivityTimerSerializer(
                    profile.activity_timer, context={"request": request}
                ).data,
                "quest_timer": QuestTimerSerializer(
                    character.quest_timer, context={"request": request}
                ).data,
            }
            return Response(data)

        except Exception as e:
            logger.error(f"[FETCH INFO] Serialization error: {e}", exc_info=True)
            return Response(
                {"error": "An error occurred during serialization."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _handle_quest_timer_expiry(self, profile, character):
        """
        If the quest timer has finished but not marked complete, finalise it.
        """
        qt = character.quest_timer
        if not (qt.time_finished() and qt.status != "completed"):
            return

        try:
            qt.elapsed_time = qt.duration
            qt.save()

            async_to_sync(send_group_message)(
                f"profile_{profile.id}",
                {"type": "action", "action": "quest_complete"},
            )

        except Exception as e:
            logger.error(f"Error handling quest timer completion: {e}", exc_info=True)
            raise

    def _ensure_activity_timer_consistency(self, profile):
        """Ensure activity timer is not in an invalid state."""
        try:
            at = profile.activity_timer
        except ObjectDoesNotExist:
            return

        activity = getattr(at, "activity", None)

        # Timer says it's running but no activity exists -> reset

        if at.status != "empty" and activity is None:
            try:
                at.reset()
            except Exception as e:
                logger.error(
                    f"[FETCH INFO] Error resetting activity timer: {e}", exc_info=True
                )
                raise


class DownloadUserDataAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(ratelimit(key="ip", rate="10/h", method="GET", block=True))
    @transaction.atomic
    def get(self, request):
        user = request.user
        profile = user.profile
        try:
            character_obj = PlayerCharacterLink().get_character(profile)
        except Character.DoesNotExist:
            logger.error(
                f"Character not found for user {user.username} (ID: {user.id}).",
                exc_info=True,
            )
            raise Http404("Character data not found.")

        activities_json = ActivitySerializer(profile.activities.all(), many=True).data
        user_data = {
            "email": user.email,
            "profile": {
                "id": profile.id,
                "profile_name": profile.name,
                "level": profile.level,
                "xp": profile.xp,
                "bio": profile.bio,
                "total_time": profile.total_time,
                "total_activities": profile.total_activities,
                "is_premium": profile.is_premium,
            },
            "activities": activities_json,
            "character": {
                "id": character_obj.id,
                "character_name": character_obj.name,
                "level": character_obj.level,
                "total_quests": character_obj.total_quests,
            },
        }

        logger.info(
            f"User {user.username} (ID: {user.id}) initiated download of their data."
        )
        logger.info(
            f"User {user.username} (ID: {user.id}) successfully downloaded their data."
        )

        return Response(user_data)


class DeleteAccountAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        logger.info(f"User {user.username} (ID: {user.id}) initiated account deletion.")

        user.pending_deletion = True
        user.delete_at = timezone.now() + timezone.timedelta(days=14)
        user.save()

        send_mail(
            "Account Deletion Scheduled",
            "Hello,\nYour account will be deleted in 14 days. If you wish to cancel the deletion, please log in again.\nThank you for using Progress, and we're sorry to see you go!",
            "admin@progressrpg.com",
            [user.email],
            fail_silently=False,
        )

        # Flush session
        request.session.flush()
        logout(request)

        logger.info(
            f"[DELETE ACCOUNT] User {user.id} logged out and scheduled for soft delete."
        )

        return Response(
            {"detail": "Account deletion scheduled. You have been logged out."},
            status=status.HTTP_200_OK,
        )

    def get(self, request):
        # Optional: could return some info or just method not allowed
        return Response(
            {"detail": "Use POST to delete your account."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )
