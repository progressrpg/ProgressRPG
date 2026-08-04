# api/views.py
from datetime import timedelta

from asgiref.sync import async_to_sync
from django.conf import settings
from django.contrib.auth import login, logout
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.db import transaction, IntegrityError
from django.http import Http404
from django.shortcuts import get_object_or_404

from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django_ratelimit.decorators import ratelimit
from urllib.parse import quote, unquote

from allauth.account import app_settings as allauth_settings
from allauth.account.adapter import get_adapter
from allauth.account.models import EmailConfirmation, EmailAddress

# from allauth.account.utils import complete_signup, send_email_confirmation
from dj_rest_auth.registration.views import RegisterView

from rest_framework import viewsets, permissions, status, serializers as drf_serializers
from rest_framework.decorators import (
    api_view,
    action,
)

from drf_spectacular.utils import extend_schema, inline_serializer

# from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

# from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from api.serializers import (
    AnnouncementListResponseSerializer,
    AnnouncementSerializer,
    AnnouncementUnreadCountSerializer,
    UserSerializer,
    UserSettingsSerializer,
    Step1Serializer,
    ConfirmEmailResponseSerializer,
    ConfirmEmailAlreadyConfirmedSerializer,
    FetchInfoResponseSerializer,
    DownloadUserDataResponseSerializer,
    DeleteAccountResponseSerializer,
    GameSettingsSerializer,
    WaitlistSignupRequestSerializer,
    WaitlistSignupResponseSerializer,
    RegistrationStatusResponseSerializer,
    WaitlistJoinRequestSerializer,
    WaitlistJoinResponseSerializer,
    CustomRegisterSerializer,
    CustomTokenObtainPairSerializer,
    CustomTokenRefreshSerializer,
    MarkAnnouncementReadRequestSerializer,
    MarkAnnouncementReadResponseSerializer,
    MarkAllAnnouncementsReadResponseSerializer,
)
from api.mailchimp import (
    MailchimpConfigurationError,
    MailchimpRequestError,
    subscribe_email_to_waitlist,
)

from character.models import Character, PlayerCharacterLink
from character.serializers import CharacterSerializer
from core.models import Announcement, GameSettings, PlayerAnnouncementState

from gameplay.serializers import ActivityTimerSerializer
from gameplay.services.xp_modifiers import handle_online_login
from users.services.login_services import get_login_state

from progression.serializers import PlayerActivitySerializer

from users.models import Player, TutorialStep, Waitlist
from users.serializers import PlayerSerializer, TutorialStepSerializer
from users.services import waitlist_service
from users.services.registration_services import verified_user_count
from users.utils import send_email_to_users

from progress_rpg.settings.utils import get_build_number

from metrics.utils import track_user_session
from server_management.models import FeatureFlag

import logging

logger = logging.getLogger("errors")
logger_general = logging.getLogger("general")


class AppConfigView(APIView):
    permission_classes = []

    @extend_schema(
        responses=inline_serializer(
            name="AppConfigResponse",
            fields={
                "stripe_live_mode": drf_serializers.BooleanField(),
                "stripe_billing_portal_url": drf_serializers.URLField(),
                "feature_flags": drf_serializers.DictField(),
                "trial_period_days": drf_serializers.IntegerField(),
            },
        )
    )
    def get(self, request):
        from core.models import GameSettings

        game_settings = GameSettings.current()
        return Response(
            {
                "stripe_live_mode": settings.STRIPE_LIVE_MODE,
                "stripe_billing_portal_url": settings.STRIPE_BILLING_PORTAL_URL,
                "feature_flags": FeatureFlag.as_dict(),
                "trial_period_days": game_settings.trial_period_days,
            }
        )


class WaitlistSignupAPIView(APIView):
    permission_classes = [AllowAny]
    serializer_class = WaitlistSignupResponseSerializer
    request_serializer_class = WaitlistSignupRequestSerializer

    @method_decorator(ratelimit(key="ip", rate="10/h", method="POST", block=True))
    def post(self, request):
        serializer = self.request_serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        email_domain = email.split("@")[-1] if "@" in email else ""

        try:
            response_data = subscribe_email_to_waitlist(email)
        except MailchimpConfigurationError:
            logger.error(
                "[WAITLIST] Missing Mailchimp configuration email_domain=%s",
                email_domain,
            )
            return Response(
                {"detail": "Waitlist signup is temporarily unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except MailchimpRequestError as exc:
            logger.warning(
                "[WAITLIST] Mailchimp rejected signup email_domain=%s status=%s",
                email_domain,
                exc.response_status,
            )
            return Response(
                {"detail": exc.user_message},
                status=exc.response_status,
            )

        return Response(response_data, status=status.HTTP_200_OK)


class RegistrationStatusAPIView(APIView):
    permission_classes = [AllowAny]
    serializer_class = RegistrationStatusResponseSerializer

    def get(self, request):
        game_settings = GameSettings.current()
        registration_open = verified_user_count() < game_settings.registration_cap
        return Response(
            {
                "registration_open": registration_open,
                "registration_enabled": game_settings.registration_enabled,
                "self_serve_registration": game_settings.self_serve_registration,
                "waitlist_signup_provider": game_settings.waitlist_signup_provider,
                # The site key is public, and serving it here keeps it out of
                # the frontend build: rotating the key or enabling Turnstile
                # needs only a backend env change, no rebuild.
                "turnstile_site_key": settings.CF_TURNSTILE_SITE_KEY or "",
            }
        )


class WaitlistJoinAPIView(APIView):
    permission_classes = [AllowAny]
    serializer_class = WaitlistJoinResponseSerializer
    request_serializer_class = WaitlistJoinRequestSerializer

    @method_decorator(ratelimit(key="ip", rate="10/h", method="POST", block=True))
    def post(self, request):
        serializer = self.request_serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()

        already_waiting = Waitlist.objects.filter(
            email=email, status__in=[Waitlist.Status.WAITING, Waitlist.Status.INVITED]
        ).exists()
        if not already_waiting:
            try:
                entry = Waitlist.objects.create(email=email, status=Waitlist.Status.WAITING)
            except IntegrityError:
                pass  # race with a concurrent signup — treat as already-waiting
            else:
                waitlist_service.send_signup_confirmation_email(entry)

        return Response(
            {"detail": "You're on the waitlist."}, status=status.HTTP_200_OK
        )


class GameSettingsAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = GameSettingsSerializer

    def get(self, request):
        settings_obj = GameSettings.current()
        return Response(self.serializer_class(settings_obj).data)


class IsOwnerPlayer(permissions.BasePermission):
    owner_attr = "player"

    def has_object_permission(self, request, view, obj):
        player = getattr(request.user, "player", None)
        if player is None:
            return False

        if hasattr(obj, "player"):
            return obj.player == player

        return False


class IsOwnerCharacter(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        player = getattr(request.user, "player", None)
        if player is None:
            return False

        if hasattr(obj, "character"):
            return PlayerCharacterLink.objects.filter(
                player=player, character=obj.character, is_active=True
            ).exists()

        return False


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        email = (request.data or {}).get("email", "")
        email_domain = (
            email.split("@")[-1] if isinstance(email, str) and "@" in email else ""
        )

        try:
            response = super().post(request, *args, **kwargs)
            logger_general.info(
                "[AUTH JWT CREATE] path=%s host=%s status=%s content_type=%s has_email=%s email_domain=%s",
                request.path,
                request.get_host(),
                response.status_code,
                response.get("Content-Type", ""),
                bool(email),
                email_domain,
            )
            return response
        except Exception:
            logger.exception(
                "[AUTH JWT CREATE] exception path=%s host=%s has_email=%s email_domain=%s",
                request.path,
                request.get_host(),
                bool(email),
                email_domain,
            )
            raise

    @csrf_exempt
    @api_view(["POST"])
    @staticmethod
    def test_post_view(request):
        permission_classes = [IsAuthenticated]
        return Response(
            {"status": "ok", "message": f"Hello {request.user.email}! POST successful!"}
        )


class CustomTokenRefreshView(TokenRefreshView):
    serializer_class = CustomTokenRefreshSerializer


class MeViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    @extend_schema(responses=UserSerializer)
    def list(self, request):
        user = request.user
        serializer = UserSerializer(user)
        return Response(serializer.data)

    @extend_schema(request=UserSettingsSerializer, responses=UserSerializer)
    @action(detail=False, methods=["patch"])
    def user_settings(self, request):
        serializer = UserSettingsSerializer(
            request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(UserSerializer(request.user).data)

    @extend_schema(responses=PlayerSerializer)
    @action(detail=False, methods=["get", "patch"])
    def player(self, request):
        player = request.user.player

        if request.method == "PATCH":
            serializer = PlayerSerializer(player, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        serializer = PlayerSerializer(player)
        return Response(serializer.data)

    @extend_schema(responses=CharacterSerializer)
    @action(detail=False, methods=["get"])
    def character(self, request):
        player = request.user.player
        character = player.current_character  # or however you store it

        if not character:
            return Response(
                {"detail": "No current character set for this player."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            CharacterSerializer(character, context={"request": request}).data
        )

    @extend_schema(
        responses=inline_serializer(
            name="TodayPointsResponse",
            fields={
                "points_today": drf_serializers.IntegerField(allow_null=True),
            },
        )
    )
    @action(detail=False, methods=["get"])
    def today_points(self, request):
        """
        Personal "points earned today" for the map view's badge (issue #673).
        `points_today` is null - not zero - when the player has no active
        PlayerCharacterLink, so the frontend can tell "no link" apart from
        "linked but nothing earned yet today" and hide the badge entirely.
        """
        player = request.user.player
        link = player.active_link

        return Response({"points_today": link.points_today if link else None})

    @extend_schema(
        responses=inline_serializer(
            name="OnboardingCompletedResponse",
            fields={"onboarding_completed": drf_serializers.BooleanField()},
        )
    )
    @action(detail=False, methods=["post"])
    def complete_onboarding(self, request):
        player = request.user.player

        player.onboarding_completed = True
        player.save(update_fields=["onboarding_completed"])

        return Response(
            {"onboarding_completed": True},
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        request=inline_serializer(
            name="MarkTutorialStepsSeenRequest",
            fields={
                "step_ids": drf_serializers.ListField(
                    child=drf_serializers.IntegerField()
                )
            },
        ),
        responses=inline_serializer(
            name="MarkTutorialStepsSeenResponse",
            fields={"marked": drf_serializers.IntegerField()},
        ),
    )
    @action(detail=False, methods=["post"])
    def mark_tutorial_steps_seen(self, request):
        step_ids = request.data.get("step_ids", [])
        player = request.user.player
        steps = TutorialStep.objects.filter(id__in=step_ids)
        player.tutorial_steps_seen.add(*steps)
        return Response({"marked": steps.count()})

    @extend_schema(responses=AnnouncementListResponseSerializer)
    @action(detail=False, methods=["get"])
    def announcements(self, request):
        player = request.user.player

        published_announcements = list(Announcement.objects.filter(is_published=True))
        read_ids = set(
            PlayerAnnouncementState.objects.filter(
                player=player,
                read_at__isnull=False,
                announcement__is_published=True,
            ).values_list("announcement_id", flat=True)
        )

        serialized = AnnouncementSerializer(
            published_announcements,
            many=True,
            context={"read_ids": read_ids},
        ).data

        return Response(
            {
                "unread_count": PlayerAnnouncementState.unread_count_for_player(player),
                "results": serialized,
            }
        )

    @extend_schema(responses=AnnouncementUnreadCountSerializer)
    @action(detail=False, methods=["get"])
    def announcements_unread_count(self, request):
        player = request.user.player
        return Response(
            {"unread_count": PlayerAnnouncementState.unread_count_for_player(player)}
        )

    @extend_schema(
        request=MarkAnnouncementReadRequestSerializer,
        responses=MarkAnnouncementReadResponseSerializer,
    )
    @action(detail=False, methods=["post"])
    def mark_announcement_read(self, request):
        serializer = MarkAnnouncementReadRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        player = request.user.player
        announcement = get_object_or_404(
            Announcement.objects.filter(is_published=True),
            id=serializer.validated_data["announcement_id"],
        )

        state, _ = PlayerAnnouncementState.objects.get_or_create(
            player=player,
            announcement=announcement,
        )
        if state.read_at is None:
            state.read_at = timezone.now()
            state.save(update_fields=["read_at", "updated_at"])

        return Response(
            {
                "success": True,
                "unread_count": PlayerAnnouncementState.unread_count_for_player(player),
            }
        )

    @extend_schema(responses=MarkAllAnnouncementsReadResponseSerializer)
    @action(detail=False, methods=["post"])
    def mark_all_announcements_read(self, request):
        player = request.user.player
        now = timezone.now()

        published = Announcement.objects.filter(is_published=True)
        existing_states = PlayerAnnouncementState.objects.filter(
            player=player,
            announcement__in=published,
        )
        existing_states.filter(read_at__isnull=True).update(read_at=now)

        existing_ids = existing_states.values_list("announcement_id", flat=True)
        missing = published.exclude(id__in=existing_ids)
        PlayerAnnouncementState.objects.bulk_create(
            [
                PlayerAnnouncementState(
                    player=player,
                    announcement=announcement,
                    read_at=now,
                )
                for announcement in missing
            ],
            ignore_conflicts=True,
        )

        return Response(
            {
                "success": True,
                "unread_count": PlayerAnnouncementState.unread_count_for_player(player),
            }
        )


class TutorialStepViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TutorialStep.objects.all()
    serializer_class = TutorialStepSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "request": self.request}


class CustomRegisterView(RegisterView):
    serializer_class = CustomRegisterSerializer

    @method_decorator(ratelimit(key="ip", rate="5/h", method="POST", block=True))
    def create(self, request, *args, **kwargs):
        if not GameSettings.current().registration_enabled:
            return Response(
                {"detail": "Registration is temporarily unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        with transaction.atomic():
            user = serializer.save(self.request)

        backend_path = settings.AUTHENTICATION_BACKENDS[0]
        user.backend = backend_path

        email_address, created = EmailAddress.objects.get_or_create(
            user=user,
            email=user.email,
            defaults={"verified": False, "primary": True},
        )

        logger.debug(f"[REGISTER] EmailAddress: {email_address} (created={created})")

        confirmation = EmailConfirmation.objects.create(
            email_address=email_address,
            key=get_adapter().generate_emailconfirmation_key(email_address.email),
            sent=timezone.now(),
        )

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
    serializer_class = ConfirmEmailResponseSerializer

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

    def get_player(self, request):
        return request.user.player

    @action(detail=False, methods=["get"])
    def status(self, request):
        player = self.get_player(request)
        if player.onboarding_step == 0:
            player.onboarding_step = 1
            player.save()
        return Response(
            {
                "step": player.onboarding_step,
            }
        )

    @action(detail=False, methods=["post"])
    def progress(self, request):
        player = self.get_player(request)

        if player.onboarding_step == 1:
            serializer = Step1Serializer(player, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                player.onboarding_step = 2
                player.save()
                return Response(
                    {
                        "message": "Player named.",
                        "step": player.onboarding_step,
                    }
                )
        return Response(serializer.errors, status=400)


##########################################################
##### FETCH INFO VIEW
##########################################################


class FetchInfoAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FetchInfoResponseSerializer

    def get(self, request, format=None):
        player = request.user.player
        build_number = get_build_number()

        logger.info(f"[FETCH INFO] Fetching data for player {player.id}")

        # --- Track user session ---
        track_user_session(player)

        # --- Ensure activity timer is in a valid state ---
        self._ensure_activity_timer_consistency(player)

        player.last_seen = timezone.now()
        player.save(update_fields=["last_seen"])

        handle_online_login(player)

        login_state_data = get_login_state(request.user)

        # --- Serialize everything ---
        game_settings = GameSettings.current()
        try:
            data = {
                "success": True,
                "message": "Player and character fetched",
                "build_number": build_number,
                "player": PlayerSerializer(player, context={"request": request}).data,
                "character": None,
                "activity_timer": ActivityTimerSerializer(
                    player.activity_timer, context={"request": request}
                ).data,
                "population_centre": None,
                "xp_mods": [],
                "login_state": login_state_data["login_state"],
                "login_streak": login_state_data["login_streak"],
                "login_event_at": login_state_data["login_event_at"],
                "login_reward_xp": login_state_data["login_reward_xp"],
                "announcement_unread_count": PlayerAnnouncementState.unread_count_for_player(
                    player
                ),
                "free_timer_limit_seconds": game_settings.free_timer_limit_seconds,
                "game_settings": GameSettingsSerializer(game_settings).data,
                "online_count": Player.online_count(),
            }
            return Response(data)

        except Exception as e:
            logger.error(f"[FETCH INFO] Serialization error: {e}", exc_info=True)
            return Response(
                {"error": "An error occurred during serialization."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _ensure_activity_timer_consistency(self, player):
        """Ensure activity timer is not in an invalid state."""
        try:
            at = player.activity_timer
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


##########################################################
##### USER DATA MANAGEMENT VIEWS
##########################################################


class DownloadUserDataAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DownloadUserDataResponseSerializer

    @method_decorator(ratelimit(key="ip", rate="10/h", method="GET", block=True))
    @transaction.atomic
    def get(self, request):
        user = request.user
        player = user.player
        active_link = player.active_link
        character_obj = active_link.character if active_link else None

        activities_json = PlayerActivitySerializer(
            player.activities.all(), many=True
        ).data
        user_data = {
            "email": user.email,
            "player": {
                "id": player.id,
                "player_name": player.name,
                "level": player.level,
                "xp": player.xp,
                "bio": player.bio,
                "total_time": player.total_time,
                "total_activities": player.total_activities,
                "is_premium": user.is_premium,
            },
            "activities": activities_json,
            "character": (
                {
                    "id": character_obj.id,
                    "character_name": character_obj.name,
                    "level": character_obj.level,
                    "total_activities": character_obj.total_activities,
                }
                if character_obj
                else None
            ),
        }

        logger.info(
            f"User {user.username} (ID: {user.id}) initiated download of their data."
        )
        logger.info(
            f"User {user.username} (ID: {user.id}) successfully downloaded their data."
        )

        # Return formatted JSON response for download
        response = Response(user_data)
        response["Content-Disposition"] = 'attachment; filename="user_data.json"'
        return response


class DeleteAccountAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DeleteAccountResponseSerializer

    def post(self, request):
        user = request.user

        logger.info(f"User {user.username} (ID: {user.id}) initiated account deletion.")

        user.pending_deletion = True
        user.delete_at = timezone.now() + timedelta(days=14)
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
