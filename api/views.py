# api/views.py
from asgiref.sync import async_to_sync

# from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth import login, logout, get_user_model
from django.core.mail import send_mail
from django.db import DatabaseError, transaction
from django.http import Http404  # , HttpResponseRedirect

# from django.shortcuts import render, get_object_or_404, redirect
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
    CustomTokenObtainPairSerializer,
    CustomTokenRefreshSerializer,
    CustomRegisterSerializer,
    UserSerializer,
    ProfileSerializer,
    CharacterSerializer,
    ActivitySerializer,
    QuestSerializer,
    ActivityTimerSerializer,
    QuestTimerSerializer,
    Step1Serializer,
    # Step2Serializer,
    # Step3Serializer,
    InteriorSpaceSerializer,
    BuildingSerializer,
    PopulationCentreSerializer,
    LandAreaSerializer,
    SubzoneSerializer,
)

from character.models import Character, PlayerCharacterLink
from gameplay.filters import ActivityFilter
from gameplay.models import Activity, Quest, ActivityTimer, QuestTimer
from gameplay.utils import check_quest_eligibility, send_group_message
from locations.models import (
    InteriorSpace,
    Building,
    PopulationCentre,
    LandArea,
    Subzone,
)
from progress_rpg.settings.utils import get_build_number
from server_management.models import MaintenanceWindow
from users.models import Profile
from users.utils import send_email_to_users

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


@api_view(["GET"])
def maintenance_status(request):
    # Returns whether any maintenance window is currently active
    window = MaintenanceWindow.objects.filter(is_active=True).first()
    if window:
        data = {
            "maintenance_active": True,
            "name": window.name,
            "start_time": window.start_time.isoformat(),
            "end_time": window.end_time.isoformat(),
            "description": window.description,
        }
    else:
        data = {"maintenance_active": False}
    return Response(data)


##########################################################
##### REGISTRATION VIEWS
##########################################################


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


##########################################################
##### FETCHINFO API RESPONSE
##########################################################


class FetchInfoAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        build_number = get_build_number()

        profile = request.user.profile
        try:
            character = PlayerCharacterLink.get_character(profile)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        logger.info(
            f"[FETCH INFO] Fetching data for profile {profile.id}, character {character.id}"
        )

        qt = character.quest_timer
        if qt.time_finished() and qt.status != "completed":
            try:
                qt.elapsed_time = qt.duration
                qt.save()
                async_to_sync(send_group_message)(
                    f"profile_{profile.id}",
                    {"type": "action", "action": "quest_complete"},
                )
            except Exception as e:
                logger.error(f"Error handling quest timer completion: {e}")
                return Response(
                    {
                        "error": "An error occurred while handling quest timer completion."
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        if (
            profile.activity_timer.status != "empty"
            and profile.activity_timer.activity is None
        ):
            try:
                profile.activity_timer.reset()
            except Exception as e:
                logger.error(f"Error resetting activity timer: {e}")
                return Response(
                    {"error": "An error occurred while resetting the activity timer."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        try:
            profile_data = ProfileSerializer(profile, context={"request": request}).data
            character_data = CharacterSerializer(
                character, context={"request": request}
            ).data
            activity_timer_data = ActivityTimerSerializer(
                profile.activity_timer, context={"request": request}
            ).data
            quest_timer_data = QuestTimerSerializer(
                qt, context={"request": request}
            ).data

            return Response(
                {
                    "success": True,
                    "profile": profile_data,
                    "character": character_data,
                    "message": "Profile and character fetched",
                    "activity_timer": activity_timer_data,
                    "quest_timer": quest_timer_data,
                    "build_number": build_number,
                }
            )

        except Exception as e:
            logger.error(f"Serialization error: {e}")
            return Response(
                {"error": "An error occurred during serialization."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


##########################################################
##### PROFILE & CHARACTER VIEWSETS
##########################################################


class ProfileViewSet(
    mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Restrict access to only the logged-in user's profile
        return Profile.objects.filter(user=self.request.user)


class CharacterViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Viewset for listing and retrieving characters.
    Characters can be browsed by authenticated users — for example,
    to view their history or find nearby players.

    Modifications to characters should happen only via gameplay endpoints
    (e.g. quest completion, XP gain), not through direct update.
    """

    serializer_class = CharacterSerializer
    permission_classes = [IsAuthenticated]
    queryset = Character.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # Example: later you might filter by proximity or visibility
        # location = user.profile.location
        # queryset = queryset.filter(location__near=location)

        return queryset


##########################################################
##### ACTIVITY AND QUEST VIEWSETS
##########################################################


class ActivityViewSet(viewsets.ModelViewSet):
    serializer_class = ActivitySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ActivityFilter
    permission_classes = [IsAuthenticated, IsOwnerProfile]

    def perform_create(self, serializer):
        serializer.save(profile=self.request.user.profile)

    def get_queryset(self):
        profile = self.request.user.profile
        queryset = Activity.objects.filter(profile=profile)

        return queryset.order_by("-created_at")

    def create(self, request, *args, **kwargs):
        profile = request.user.profile
        activity_name_raw = request.data.get("activityName")

        if not activity_name_raw:
            return Response(
                {"error": "Activity name is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        activity_name = escape(activity_name_raw)

        try:
            activity = Activity.objects.create(profile=profile, name=activity_name)
            profile.activity_timer.new_activity(activity)
            profile.activity_timer.refresh_from_db()
        except DatabaseError:
            return Response(
                {"error": "A database error occurred while creating the activity."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            activity_timer_data = ActivityTimerSerializer(
                profile.activity_timer, context={"request": request}
            ).data
        except ValidationError:
            return Response(
                {"error": "Invalid data encountered during serialization."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "success": True,
                "message": "Activity timer created and ready",
                "activity_timer": activity_timer_data,
            }
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="submit",
        permission_classes=[IsAuthenticated],
    )
    def submit(self, request, pk=None):
        profile = request.user.profile

        try:
            activity = self.get_object()  # Get activity by pk for current user
        except Activity.DoesNotExist:
            return Response(
                {"error": "Activity not found."}, status=status.HTTP_404_NOT_FOUND
            )

        activity_name = request.data.get("name")
        if not activity_name:
            return Response(
                {"error": "Activity name is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            activity.update_name(activity_name)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Return latest activities (today’s or recent 5)
        activities = Activity.objects.filter(
            profile=profile, completed_at__date=timezone.now().date()
        ).order_by("-completed_at")
        if not activities.exists():
            activities = Activity.objects.filter(profile=profile).order_by(
                "-completed_at"
            )[:5]

        activities_list = ActivitySerializer(activities, many=True).data
        profile_data = ProfileSerializer(profile).data

        return Response(
            {
                "success": True,
                "message": "Activity submitted",
                "profile": profile_data,
                "activities": activities_list,
            }
        )


class QuestViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = QuestSerializer

    def get_queryset(self):
        return Quest.objects.all()

    def list(self, request):
        quests = self.get_queryset()
        serializer = QuestSerializer(quests, many=True, context={"request": request})
        return Response({"quests": serializer.data})

    @action(detail=False, methods=["get"])
    def eligible(self, request):
        profile = request.user.profile
        try:
            character = PlayerCharacterLink.get_character(profile)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        eligible_quests = check_quest_eligibility(character, profile)
        serializer = QuestSerializer(
            eligible_quests, many=True, context={"request": request}
        )
        return Response({"eligible_quests": serializer.data})

    @action(detail=False, methods=["post"])
    def complete(self, request):
        profile = request.user.profile
        try:
            character = PlayerCharacterLink.get_character(profile)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            profile.activity_timer.refresh_from_db()
            character.quest_timer.refresh_from_db()
            completion_data = character.complete_quest()
            if not completion_data:
                raise ValidationError("Quest completion failed - data was None.")
        except Exception as e:
            return Response(
                {"error": "Failed to complete quest: " + str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        eligible_quests = check_quest_eligibility(character, profile)
        quests_data = QuestSerializer(
            eligible_quests, many=True, context={"request": request}
        ).data
        character_data = CharacterSerializer(
            character, context={"request": request}
        ).data

        return Response(
            {
                "success": True,
                "message": "Quest completed",
                "quests": quests_data,
                "character": character_data,
                "activity_timer_status": profile.activity_timer.status,
                "quest_timer_status": character.quest_timer.status,
                "completion_data": completion_data,
            }
        )


##########################################################
##### TIMER VIEWSETS
##########################################################


class BaseTimerViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Abstract base class for timer viewsets. Assumes each timer
    is linked to a profile, and enforces IsAuthenticated + IsOwnerProfile.
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Default queryset logic (override if needed)
        return self.queryset.filter(profile=self.request.user.profile)

    def handle_related_object(self, related_model, related_id, related_name="object"):
        """
        Generic helper to fetch a related model instance and return a DRF Response on failure.
        """
        try:
            return related_model.objects.get(id=related_id), None
        except related_model.DoesNotExist:
            return None, Response(
                {"error": f"{related_name.capitalize()} not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def control_timer(self, request, pk, command):
        timer = self.get_object()

        # Map commands to timer methods
        commands_map = {
            "start": timer.start,
            "pause": timer.pause,
            "reset": timer.reset,
        }

        if command not in commands_map:
            return Response({"error": "Invalid timer command"}, status=400)

        try:
            commands_map[command]()
            timer.refresh_from_db()
            serializer = self.get_serializer(timer)
            return Response({"success": True, "timer": serializer.data})
        except Exception as e:
            return Response({"error": str(e)}, status=400)

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        return self.control_timer(request, pk, "start")

    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None):
        return self.control_timer(request, pk, "pause")

    @action(detail=True, methods=["post"])
    def reset(self, request, pk=None):
        return self.control_timer(request, pk, "reset")


class ActivityTimerViewSet(BaseTimerViewSet):
    serializer_class = ActivityTimerSerializer
    queryset = ActivityTimer.objects.all()
    permission_classes = [IsAuthenticated, IsOwnerProfile]

    def get_queryset(self):
        timer = ActivityTimer.objects.filter(profile=self.request.user.profile)
        # logger.debug(f"activitytimer viewset, timer: {timer}")
        return timer

    @action(detail=True, methods=["post"])
    def set_activity(self, request, pk=None):
        timer = self.get_object()
        name = request.data.get("activityName")

        if not name:
            return Response({"error": "Missing activity name"}, status=400)

        act_timer_updated = timer.new_activity(name)

        logger.debug(f"activitytimer set_activity, timer: {act_timer_updated.activity}")
        act_timer_updated.refresh_from_db()
        serializer = self.get_serializer(act_timer_updated)
        return Response({"success": True, "activity_timer": serializer.data})

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        timer = self.get_object()
        try:
            timer.complete()
            serializer = self.get_serializer(timer)
            return Response({"success": True, "timer": serializer.data})
        except Exception as e:
            return Response({"error": str(e)}, status=400)


class QuestTimerViewSet(BaseTimerViewSet):
    serializer_class = QuestTimerSerializer
    queryset = QuestTimer.objects.all()
    permission_classes = [IsAuthenticated, IsOwnerCharacter]

    def get_queryset(self):
        profile = self.request.user.profile
        active_character_ids = PlayerCharacterLink.objects.filter(
            profile=profile, is_active=True
        ).values_list("character_id", flat=True)

        return QuestTimer.objects.filter(character_id__in=active_character_ids)

    @action(detail=True, methods=["post"])
    def change_quest(self, request, pk=None):
        timer = self.get_object()

        # Confirm timer belongs to request.user.profile's character
        try:
            character = PlayerCharacterLink.get_character(request.user.profile)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if timer.character != character:
            return Response(
                {"error": "You do not have permission to modify this quest timer."},
                status=status.HTTP_403_FORBIDDEN,
            )

        quest_id = request.data.get("quest_id")
        duration = request.data.get("duration")

        quest, error_response = self.handle_related_object(Quest, quest_id, "quest")
        if error_response:
            return error_response

        if not isinstance(duration, int):
            try:
                duration = int(duration)
            except (ValueError, TypeError):
                return Response(
                    {"error": "Duration must be an integer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            timer.change_quest(quest, duration)
            timer.refresh_from_db()
        except Exception as e:
            return Response(
                {"error": "Failed to change quest: " + str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        serializer = self.get_serializer(timer)
        return Response({"success": True, "quest_timer": serializer.data})

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        timer = self.get_object()
        # logger.debug(f"You have arrived in the arrivals lounge.")
        if not timer.quest:
            return Response({"error": "No quest assigned to this timer."}, status=400)
        quest_id = timer.quest.id

        quest, error_response = self.handle_related_object(Quest, quest_id, "quest")
        if error_response:
            return error_response

        try:
            qt_updated, character_updated = timer.complete()
        except Exception as e:
            return Response(
                {"error": f"Failed to complete quest: {str(e)}"}, status=500
            )

        qt_serialized = self.get_serializer(qt_updated)
        character_serialized = CharacterSerializer(character_updated)
        response = {
            "success": True,
            "quest_timer": qt_serialized.data,
            "character": character_serialized.data,
        }

        logger.debug(f"Questtimer complete, response: {response}")
        return Response(response)


##########################################################
##### USER DATA MANAGEMENT VIEWS
##########################################################


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
                f"Character not found for user {user.username} (ID: {user.id})."
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


##########################################################
##### LOCATION VIEWS AND VIEWSETS
##########################################################


from locations.models import PopulationCentre
from .serializers import (
    ObjectLocationSerializer,
    PolygonFeatureSerializer,
    BoundaryFeatureSerializer,
)


class InteriorSpaceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = InteriorSpace.objects.all()
    serializer_class = InteriorSpaceSerializer


class BuildingViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Building.objects.all()
    serializer_class = BuildingSerializer


class PopulationCentreViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PopulationCentre.objects.all()
    serializer_class = PopulationCentreSerializer


class LandAreaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LandArea.objects.all()
    serializer_class = LandAreaSerializer


class SubzoneViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Subzone.objects.all()
    serializer_class = SubzoneSerializer


class PopulationCentreMapView(APIView):
    def get(self, request, pk):
        population_centre = PopulationCentre.objects.get(pk=pk)
        buildings = population_centre.buildings.all()
        characters = population_centre.residents.all()

        features = []

        features.append(BoundaryFeatureSerializer(population_centre).data)

        character_features = ObjectLocationSerializer(characters, many=True).data
        features.extend(character_features)

        building_features = PolygonFeatureSerializer(buildings, many=True).data
        features.extend(building_features)

        # road_features = RoadFeatureSerializer(
        #     population_centre.roads.all(),
        #     many=True
        # ).data

        return Response(
            {
                "type": "FeatureCollection",
                "features": features,
            }
        )
