from asgiref.sync import async_to_sync

# from asgiref.sync import sync_to_async
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.auth.decorators import login_required

# from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, OperationalError, DatabaseError
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.utils.html import escape

# from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_GET
from rest_framework.serializers import ValidationError
import json, logging

from .models import Quest, ServerMessage

# from .models import QuestCompletion, ActivityTimer, QuestTimer
from .serializers import (
    ActivitySerializer,
    QuestSerializer,
    ActivityTimerSerializer,
    QuestTimerSerializer,
)
from .utils import check_quest_eligibility, send_group_message

from character.models import PlayerCharacterLink
from character.serializers import CharacterSerializer

# from users.models import Profile
from users.serializers import ProfileSerializer

from progression.models import Activity

logger = logging.getLogger("django")


@ensure_csrf_cookie
def get_csrf_token(request):
    return JsonResponse({"detail": "CSRF cookie set"})


# Game view
@login_required
def game_view(request):
    """
    Render the main game view for the logged-in user.
    """
    logger.info(f"[GAME VIEW] Accessed by user {request.user.profile.id}")
    return render(
        request,
        "frontend/index.html",
        {"debug": settings.DEBUG},
    )


# Fetch activities
@login_required
def fetch_activities(request):
    """
    Fetch and return all activities for the logged-in user on the current date.

    :param request: The HTTP GET request object.
    :type request: django.http.HttpRequest
    :return: A JSON response containing the activities or an error message.
    :rtype: django.http.JsonResponse
    """
    if request.method != "GET":
        logger.warning(
            f"[FETCH ACTIVITIES] Invalid method {request.method} used by user {request.user.profile.id}"
        )
        return JsonResponse({"error": "Invalid method"}, status=405)

    profile = request.user.profile
    logger.info(f"[FETCH ACTIVITIES] Request received from user {profile.id}")

    try:
        activities = Activity.objects.filter(
            profile=profile, created_at__date=timezone.now().date()
        )
        serializer = ActivitySerializer(activities, many=True).data

        # Remove current activity
        if profile.activity_timer.status not in ["empty", "completed"]:
            serializer.pop(0)

        response = {
            "success": True,
            "activities": serializer,
            "message": "Activities fetched",
        }
        logger.debug(
            f"[FETCH ACTIVITIES] {len(activities)} activities fetched for user {profile.id}"
        )
        return JsonResponse(response)

    except ObjectDoesNotExist as e:
        # Raised if `profile` or related objects don't exist.
        logger.error(f"[FETCH ACTIVITIES] Object not found: {str(e)}", exc_info=True)
        return JsonResponse({"error": "Requested object not found."}, status=404)
    except ValidationError as e:
        # Handles any serializer-related errors.
        logger.error(
            f"[FETCH ACTIVITIES] Serializer validation error: {str(e)}", exc_info=True
        )
        return JsonResponse({"error": "Invalid data provided."}, status=400)
    except DatabaseError as e:
        # Catches broader database-related issues (fallback for OperationalError).
        logger.error(f"[FETCH ACTIVITIES] Database error: {str(e)}", exc_info=True)
        return JsonResponse({"error": "A database error occurred."}, status=500)
    except Exception as e:
        logger.error(f"[FETCH ACTIVITIES] Unexpected error: {str(e)}", exc_info=True)
        return JsonResponse({"error": "An unexpected error occurred."}, status=500)


# Fetch quests
@require_GET
@login_required
def fetch_quests(request):
    """
    Fetch and return eligible quests for the character associated with the logged-in user.

    :param request: The HTTP GET request object.
    :type request: django.http.HttpRequest
    :return: A JSON response containing the eligible quests or an error message.
    :rtype: django.http.JsonResponse
    """
    profile = request.user.profile
    logger.info(f"[FETCH QUESTS] Request received from user {profile.id}")

    try:
        character = PlayerCharacterLink.get_character(profile)
    except ValueError as e:
        logger.warning(
            f"[FETCH QUESTS] No character found for profile {profile.id}: {e}"
        )
        return JsonResponse({"Error: {str(e)}"})

    try:
        logger.info(
            f"[FETCH QUESTS] Checking eligible quests for character {character.id}, {profile.id}"
        )
        eligible_quests = check_quest_eligibility(character, profile)
        quests = QuestSerializer(eligible_quests, many=True, context={"request"}).data

        data = {"success": True, "quests": quests, "message": "Eligible quests fetched"}
        response = JsonResponse(data)
        return response

    except ObjectDoesNotExist as e:
        # Raised when `character` or related objects are not found in the database.
        logger.error(f"[FETCH QUESTS] Object not found: {str(e)}", exc_info=True)
        return JsonResponse({"error": "Character or profile not found."}, status=404)
    except ValidationError as e:
        # Raised when there's an issue with the serializer validation.
        logger.error(f"[FETCH QUESTS] Validation error: {str(e)}", exc_info=True)
        return JsonResponse({"error": "Invalid quest data encountered."}, status=400)
    except OperationalError as e:
        # Handles database operation issues, such as connection failures.
        logger.error(
            f"[FETCH QUESTS] Database operational error: {str(e)}", exc_info=True
        )
        return JsonResponse(
            {"error": "Database error occurred. Please try again later."}, status=500
        )
    except DatabaseError as e:
        # Handles other database-related issues (fallback for OperationalError).
        logger.error(f"[FETCH QUESTS] General database error: {str(e)}", exc_info=True)
        return JsonResponse(
            {"error": "A database error occurred. Please try again later."}, status=500
        )
    except Exception as e:
        # Generic fallback for unexpected errors.
        logger.error(f"[FETCH QUESTS] Unexpected error: {str(e)}", exc_info=True)
        return JsonResponse(
            {"error": "An unexpected error occurred while fetching quests."}, status=500
        )


async def test_redis_connection():
    channel_layer = get_channel_layer()
    profile_id = 1

    try:
        await channel_layer.group_add("test_group", "test_channel")
        await channel_layer.group_discard("test_group", "test_channel")
        logger.info("Redis connection successful!")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}")

    try:
        # Send a test message directly to the group
        await channel_layer.group_send(
            f"profile_{profile_id}",
            {"type": "test_message", "message": "Testing Redis connection"},
        )
        logger.info(f"Test message sent to profile_{profile_id}")
        return True
    except Exception as e:
        logger.error(f"Redis connection test failed: {e}")
        return False


# Fetch info
@login_required
def fetch_info(request):
    """
    Retrieve profile, character, activity timer, and quest timer details for the logged-in user.

    :param request: The HTTP GET request object.
    :type request: django.http.HttpRequest
    :return: A JSON response containing the profile, character, and timer information.
    :rtype: django.http.JsonResponse
    """
    if request.method != "GET":
        logger.warning(
            f"[FETCH INFO] Invalid method {request.method} used by user {request.user.profile.id}"
        )
        return JsonResponse({"error": "Invalid method"}, status=405)

    profile = request.user.profile
    try:
        character = PlayerCharacterLink.get_character(profile)
    except ValueError as e:
        return JsonResponse({"Error: {str(e)}"})

    # async_to_sync(test_redis_connection)()

    try:
        logger.info(
            f"[FETCH INFO] Fetching data for profile {profile.id}, character {character.id}"
        )
        logger.debug(
            f"[FETCH INFO] Timers status: {profile.activity_timer.status}/{character.quest_timer.status}"
        )

        qt = character.quest_timer
        if qt.time_finished() and qt.status != "completed":
            try:
                logger.info(
                    f"[FETCH INFO] Quest timer expired for character {character.id}, marking quest as complete"
                )
                qt.elapsed_time = qt.duration
                qt.save()
                logger.debug(
                    f"[FETCH INFO] qt status {qt.status}, {qt.quest}, elapsed/remaining {qt.get_elapsed_time()}/{qt.get_remaining_time()}, duration {qt.duration}"
                )
                async_to_sync(send_group_message)(
                    f"profile_{profile.id}",
                    {"type": "action", "action": "quest_complete"},
                )
            except Exception as e:
                # Handle unexpected issues during quest timer update or messaging.
                logger.error(
                    f"[FETCH INFO] Error handling quest timer completion for character {character.id}: {str(e)}",
                    exc_info=True,
                )
                return JsonResponse(
                    {
                        "error": "An error occurred while handling quest timer completion."
                    },
                    status=500,
                )

        if (
            profile.activity_timer.status != "empty"
            and profile.activity_timer.activity is None
        ):
            try:
                logger.warning(
                    f"[FETCH INFO] Timer status is {profile.activity_timer.status} but activity empty ({profile.activity_timer.activity}). Resetting activity timer"
                )
                profile.activity_timer.reset()
            except Exception as e:
                # Handle errors related to resetting the activity timer.
                logger.error(
                    f"[FETCH INFO] Error resetting activity timer for profile {profile.id}: {str(e)}",
                    exc_info=True,
                )
                return JsonResponse(
                    {"error": "An error occurred while resetting the activity timer."},
                    status=500,
                )

        try:
            profile_serializer = ProfileSerializer(profile).data
            character_serializer = CharacterSerializer(character).data
            act_timer = ActivityTimerSerializer(profile.activity_timer).data
            quest_timer = QuestTimerSerializer(qt).data

            response = {
                "success": True,
                "profile": profile_serializer,
                "character": character_serializer,
                "message": "Profile and character fetched",
                "activity_timer": act_timer,
                "quest_timer": quest_timer,
            }

            logger.debug(
                f"[FETCH INFO] Response generated successfully for profile {profile.id}"
            )
            return JsonResponse(response)

        except ValidationError as e:
            # Handle serializer validation errors.
            logger.error(
                f"[FETCH INFO] Serializer validation error: {str(e)}", exc_info=True
            )
            return JsonResponse(
                {"error": "Invalid data encountered during serialization."}, status=400
            )
        except Exception as e:
            # Catch unexpected errors during serialization or response generation.
            logger.error(
                f"[FETCH INFO] Error generating response for profile {profile.id}: {str(e)}",
                exc_info=True,
            )
            return JsonResponse(
                {
                    "error": "An unexpected error occurred while generating the response."
                },
                status=500,
            )

    except ObjectDoesNotExist as e:
        # Handle cases where `character` or `profile` objects do not exist.
        logger.error(f"[FETCH INFO] Object not found: {str(e)}", exc_info=True)
        return JsonResponse({"error": "Character or profile not found."}, status=404)
    except OperationalError as e:
        # Handle database-related operational issues.
        logger.error(
            f"[FETCH INFO] Database operational error: {str(e)}", exc_info=True
        )
        return JsonResponse(
            {"error": "Database error occurred. Please try again later."}, status=500
        )
    except DatabaseError as e:
        # Handle general database-related errors.
        logger.error(f"[FETCH INFO] General database error: {str(e)}", exc_info=True)
        return JsonResponse(
            {"error": "A database error occurred. Please try again later."}, status=500
        )
    except Exception as e:
        # Catch-all for unexpected errors.
        logger.error(f"[FETCH INFO] Unexpected error: {str(e)}", exc_info=True)
        return JsonResponse(
            {"error": "An unexpected error occurred while fetching information."},
            status=500,
        )


@login_required
# @transaction.atomic
@csrf_exempt
def create_activity(request):
    """
    Creates a new activity for the logged-in user and updates the activity timer.

    :param request: The HTTP POST request containing the activity name.
    :type request: django.http.HttpRequest
    :return: A JSON response containing the activity timer details or an error message.
    :rtype: django.http.JsonResponse
    """
    if request.method != "POST":
        logger.warning(
            f"[CREATE ACTIVITY] Invalid method {request.method} used by user {request.user.profile.id}"
        )
        return JsonResponse({"error": "Invalid method"}, status=405)

    profile = request.user.profile

    try:
        logger.info(
            f"[CREATE ACTIVITY] Profile {profile.id} initiated activity creation"
        )

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            logger.error(
                f"[CREATE ACTIVITY] JSON decode error for profile {profile.id}: {e}"
            )
            return JsonResponse({"error": "Invalid JSON format"}, status=400)

        activity_name_raw = data.get("activityName")

        if not activity_name_raw:
            logger.warning(
                f"[CREATE ACTIVITY] Activity name missing from request for user {profile.id}"
            )
            return JsonResponse({"error": "Activity name is required"}, status=400)

        activity_name = escape(data.get("activityName"))
        logger.debug(f"[CREATE ACTIVITY] Received activity name: {activity_name}")

        try:
            activity = Activity.objects.create(profile=profile, name=activity_name)
            profile.activity_timer.new_activity(activity)
            profile.activity_timer.refresh_from_db()
            logger.info(
                f"[CREATE ACTIVITY] Activity '{activity_name}' created for profile {profile.id}. Timer status {profile.activity_timer.status}"
            )
        except DatabaseError as e:
            logger.error(
                f"[CREATE ACTIVITY] Database error while creating activity for profile {profile.id}: {e}"
            )
            return JsonResponse(
                {"error": "A database error occurred while creating the activity."},
                status=500,
            )

        try:
            activity_timer = ActivityTimerSerializer(profile.activity_timer).data
            response = {
                "success": True,
                "message": "Activity timer created and ready",
                "activity_timer": activity_timer,
            }
            logger.debug(
                f"[CREATE ACTIVITY] Response generated for profile {profile.id}: {response}"
            )
            return JsonResponse(response)
        except ValidationError as e:
            logger.error(
                f"[CREATE ACTIVITY] Validation error while serializing activity timer for profile {profile.id}: {e}"
            )
            return JsonResponse(
                {"error": "Invalid data encountered during serialization."}, status=400
            )

    except ObjectDoesNotExist as e:
        # Handle missing objects (e.g., related Profile or Timer not found)
        logger.error(
            f"[CREATE ACTIVITY] Object not found for profile {profile.id}: {e}"
        )
        return JsonResponse({"error": "Required object not found."}, status=404)
    except OperationalError as e:
        # Handle broader database operational errors
        logger.error(
            f"[CREATE ACTIVITY] Database operational error for profile {profile.id}: {e}"
        )
        return JsonResponse(
            {"error": "A database error occurred. Please try again later."}, status=500
        )
    except Exception as e:
        # Catch-all for any unexpected errors
        logger.exception(
            f"[CREATE ACTIVITY] Unexpected error for profile {profile.id}: {e}"
        )
        return JsonResponse({"error": "An unexpected error occurred"}, status=500)


@login_required
@csrf_exempt
def submit_activity(request):
    """
    Submits the current activity for the logged-in user, awarding XP and resetting timers.

    :param request: The HTTP POST request to submit the activity.
    :type request: django.http.HttpRequest
    :return: A JSON response containing the updated profile, activity rewards, and activities list.
    :rtype: django.http.JsonResponse
    """
    if request.method != "POST":
        logger.warning(
            f"[SUBMIT ACTIVITY] Invalid method {request.method} used by user {request.user.profile.id}"
        )
        return JsonResponse({"error": "Invalid method"}, status=405)

    profile = request.user.profile

    try:
        logger.info(f"[SUBMIT ACTIVITY] Profile {profile.id} submitting activity")
        logger.debug(
            f"[SUBMIT ACTIVITY] Activity timer: status {profile.activity_timer.status}, elapsed time {profile.activity_timer.elapsed_time}"
        )

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            logger.error(
                f"[SUBMIT ACTIVITY] JSON decode error for user {profile.id}: {e}"
            )
            return JsonResponse({"error": "Invalid JSON format"}, status=400)

        logger.debug(f"[SUBMIT ACTIVITY] Request body: {data}")
        logger.debug(f"[SUBMIT ACTIVITY] Body activity: {data['name']}")
        profile.activity_timer.activity.update_name(data["name"])

        try:
            profile.add_activity(profile.activity_timer.elapsed_time)
            xp_reward = profile.activity_timer.complete()
            profile.activity_timer.refresh_from_db()
            profile.add_xp(xp_reward)
            logger.debug(
                f"[SUBMIT ACTIVITY] After activity submission and reset: status: {profile.activity_timer.status}, elapsed_time: {profile.activity_timer.elapsed_time}, XP reward: {xp_reward}"
            )
        except DatabaseError as e:
            logger.error(
                f"[SUBMIT ACTIVITY] Database error while submitting activity for profile {profile.id}: {e}"
            )
            return JsonResponse(
                {"error": "A database error occurred while submitting activity."},
                status=500,
            )

        try:
            activities = Activity.objects.filter(
                profile=profile, created_at__date=timezone.now().date()
            ).order_by("-created_at")
            if not activities.exists():
                activities = Activity.objects.filter(profile=profile).order_by(
                    "-created_at"
                )[:5]
                logger.debug(
                    f"[SUBMIT ACTIVITY] No activities for today. Showing recent activities: {activities}"
                )
            activities_list = ActivitySerializer(activities, many=True).data
        except ObjectDoesNotExist as e:
            logger.error(
                f"[SUBMIT ACTIVITY] Object not found while fetching activities for profile {profile.id}: {e}"
            )
            return JsonResponse({"error": "Required activities not found."}, status=404)
        except ValidationError as e:
            logger.error(
                f"[SUBMIT ACTIVITY] Validation error while serializing activities for profile {profile.id}: {e}"
            )
            return JsonResponse(
                {"error": "Invalid data encountered during serialization."}, status=400
            )

        message_text = f"Activity submitted. You got {xp_reward} XP!"
        ServerMessage.objects.create(
            group=profile.group_name,
            type="notification",
            action="notification",
            data={},
            message=message_text,
            is_draft=False,
        )

        try:
            profile_serializer = ProfileSerializer(profile).data
            response = {
                "success": True,
                "message": "Activity submitted",
                "profile": profile_serializer,
                "activities": activities_list,
                "activity_rewards": xp_reward,
            }
            logger.debug(
                f"[SUBMIT ACTIVITY] Response generated for profile {profile.id}: {response}"
            )
            return JsonResponse(response)
        except ValidationError as e:
            logger.error(
                f"[SUBMIT ACTIVITY] Validation error while serializing response for profile {profile.id}: {e}"
            )
            return JsonResponse(
                {"error": "Invalid data encountered during response serialization."},
                status=400,
            )

    except ObjectDoesNotExist as e:
        # Handle cases where `profile` or other objects are not found
        logger.error(
            f"[SUBMIT ACTIVITY] Object not found for profile {profile.id}: {e}"
        )
        return JsonResponse({"error": "Required object not found."}, status=404)
    except OperationalError as e:
        # Handle broader database operational errors
        logger.error(
            f"[SUBMIT ACTIVITY] Database operational error for profile {profile.id}: {e}"
        )
        return JsonResponse(
            {"error": "A database error occurred. Please try again later."}, status=500
        )
    except Exception as e:
        # Catch-all for any unexpected errors
        logger.error(
            f"[SUBMIT ACTIVITY] Unexpected error for profile {profile.id}: {e}",
            exc_info=True,
        )
        return JsonResponse(
            {"error": "An unexpected error occurred while submitting activity"},
            status=500,
        )


# Choose quest
@login_required
@csrf_exempt
def choose_quest(request):
    """
    Allow the user to select a quest and update the associated quest timer.

    :param request: The HTTP POST request object with quest ID and duration.
    :type request: django.http.HttpRequest
    :return: A JSON response indicating the status of the quest selection.
    :rtype: django.http.JsonResponse
    """
    if request.method != "POST":
        logger.warning(
            f"[CHOOSE QUEST] Invalid method {request.method} used by user {request.user.profile.id}"
        )
        return JsonResponse({"error": "Invalid request"}, status=400)

    if request.headers.get("Content-Type") != "application/json":
        logger.warning(
            f"[CHOOSE QUEST] Invalid content type: {request.headers.get('Content-Type')}"
        )
        return JsonResponse({"error": "Invalid content type"}, status=400)

    profile = request.user.profile

    try:
        logger.info(
            f"[CHOOSE QUEST] User {request.user.profile.id} initiated quest selection."
        )

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            logger.error(f"[CHOOSE QUEST] JSON decode error for user {profile.id}: {e}")
            return JsonResponse({"error": "Invalid JSON format"}, status=400)

        quest_id = escape(data.get("quest_id"))

        try:
            quest = get_object_or_404(Quest, id=quest_id)
        except ObjectDoesNotExist as e:
            logger.warning(
                f"[CHOOSE QUEST] Quest ID {quest_id} not found for user {profile.id}: {e}"
            )
            return JsonResponse(
                {"success": False, "message": "Error: quest not found"}, status=404
            )
        if not quest:
            logger.warning(
                f"[CHOOSE QUEST] Quest ID {quest_id} not found for user {profile.id}"
            )
            return JsonResponse({"success": False, "message": "Error: quest not found"})

        try:
            character = PlayerCharacterLink.get_character(profile)
        except ValueError as e:
            return JsonResponse({"Error: {str(e)}"})
        duration = data.get("duration")
        logger.debug(
            f"[CHOOSE QUEST] Profile {profile.id} selected duration {duration}"
        )

        try:
            character.quest_timer.change_quest(
                quest, duration
            )  # status should now be 'waiting'
            character.quest_timer.refresh_from_db()
            logger.debug(
                f"[CHOOSE QUEST] Quest {quest.name} (ID: {quest.id}) selected by user {profile.id}"
            )
        except DatabaseError as e:
            logger.error(
                f"[CHOOSE QUEST] Database error while changing quest timer for user {profile.id}: {e}"
            )
            return JsonResponse(
                {"error": "A database error occurred while selecting the quest."},
                status=500,
            )

        # Serialize quest timer for the response
        try:
            quest_timer = QuestTimerSerializer(character.quest_timer).data
            response = {
                "success": True,
                "quest_timer": quest_timer,
                "message": f"Quest {quest.name} selected",
            }
            logger.debug(
                f"[CHOOSE QUEST] Response generated successfully for user {profile.id}"
            )
            qt = character.quest_timer
            logger.debug(
                f"[CHOOSE QUEST] Quest timer status/duration/elapsed/remaining: {qt.status}/{qt.duration}/{qt.get_elapsed_time()}/{qt.get_remaining_time()}"
            )
            return JsonResponse(response)

        except ValidationError as e:
            logger.error(
                f"[CHOOSE QUEST] Validation error while serializing quest timer for user {profile.id}: {e}"
            )
            return JsonResponse(
                {"error": "Invalid data encountered during serialization."}, status=400
            )

    except ObjectDoesNotExist as e:
        # Catch missing `profile` or other objects not found in the flow
        logger.error(f"[CHOOSE QUEST] Object not found for user {profile.id}: {e}")
        return JsonResponse({"error": "Required object not found."}, status=404)
    except OperationalError as e:
        # Handle broader database operational errors
        logger.error(
            f"[CHOOSE QUEST] Database operational error for user {profile.id}: {e}"
        )
        return JsonResponse(
            {"error": "A database error occurred. Please try again later."}, status=500
        )
    except Exception as e:
        # Fallback for any unexpected errors
        logger.exception(f"[CHOOSE QUEST] Unexpected error for user {profile.id}: {e}")
        return JsonResponse({"error": "An unexpected error occurred."}, status=500)


@login_required
@csrf_exempt
def complete_quest(request):
    """
    Completes the currently active quest for the logged-in user's character and processes rewards.
    """

    if request.method != "POST":
        logger.warning(
            f"[COMPLETE QUEST] Invalid method {request.method} used by user {request.user.profile.id}"
        )
        return JsonResponse({"error": "Invalid method"}, status=405)

    profile = request.user.profile
    try:
        character = PlayerCharacterLink.get_character(profile)
    except ValueError as e:
        return JsonResponse({"Error: {str(e)}"})

    try:
        logger.info(
            f"[COMPLETE QUEST] Profile {profile.id} initiating quest completion"
        )

        profile.activity_timer.refresh_from_db()
        character.quest_timer.refresh_from_db()

        logger.debug(
            f"[COMPLETE QUEST] Timers status before: {profile.activity_timer.status}/{character.quest_timer.status}"
        )

        try:
            completion_data = character.complete_quest()
            if completion_data is None:
                raise ValueError(
                    "Quest completion failed: No completion data returned."
                )
            logger.debug(
                f"[COMPLETE QUEST] Quest completed for character {character.id}, timers refreshed."
            )
        except ValueError as e:
            logger.error(f"Quest completion error: {e}")
        except IntegrityError as e:
            logger.error(
                f"[COMPLETE QUEST] IntegrityError while completing quest for character {character.id}: {str(e)}",
                exc_info=True,
            )
            return JsonResponse(
                {
                    "error": "Database integrity issue occurred while completing the quest."
                },
                status=500,
            )
        except DatabaseError as e:
            logger.error(
                f"[COMPLETE QUEST] Database error while completing quest for character {character.id}: {str(e)}",
                exc_info=True,
            )
            return JsonResponse(
                {"error": "A database error occurred while completing the quest."},
                status=500,
            )
        except Exception as e:
            logger.error(
                f"[COMPLETE QUEST] General error while completing quest for character {character.id}: {str(e)}",
                exc_info=True,
            )
            return JsonResponse(
                {"error": "An unexpected error occurred while completing the quest."},
                status=500,
            )

        # cache_key = f"eligible_quests_{profile.id}"
        # quests_cache = cache.get(cache_key)
        # if quests_cache:
        #     cache.delete(cache_key)
        #     logger.debug(f"[COMPLETE QUEST] Cache cleared for eligible quests of profile {profile.id}")

        try:
            eligible_quests = check_quest_eligibility(character, profile)
            quests = QuestSerializer(eligible_quests, many=True).data
        except ObjectDoesNotExist as e:
            logger.error(
                f"[COMPLETE QUEST] Object not found while checking eligible quests for profile {profile.id}: {str(e)}",
                exc_info=True,
            )
            return JsonResponse({"error": "Eligible quests not found."}, status=404)
        except ValidationError as e:
            logger.error(
                f"[COMPLETE QUEST] Validation error while serializing eligible quests for profile {profile.id}: {str(e)}",
                exc_info=True,
            )
            return JsonResponse(
                {
                    "error": "Invalid data encountered during eligible quests serialization."
                },
                status=400,
            )
        except Exception as e:
            logger.error(
                f"[COMPLETE QUEST] General error while checking eligible quests for profile {profile.id}: {str(e)}",
                exc_info=True,
            )
            return JsonResponse(
                {
                    "error": "An unexpected error occurred while checking eligible quests."
                },
                status=500,
            )

        try:
            characterdata = CharacterSerializer(character).data
            response = {
                "success": True,
                "message": "Quest completed",
                "xp_reward": 5,
                "quests": quests,
                "character": characterdata,
                "activity_timer_status": profile.activity_timer.status,
                "quest_timer_status": character.quest_timer.status,
                "completion_data": completion_data,
            }
            # logger.debug(f"[COMPLETE QUEST] Response generated for profile {profile.id}: {response}")
            return JsonResponse(response)
        except ValidationError as e:
            logger.error(
                f"[COMPLETE QUEST] Validation error while serializing response for profile {profile.id}: {str(e)}",
                exc_info=True,
            )
            return JsonResponse(
                {"error": "Invalid data encountered during response serialization."},
                status=400,
            )
        except Exception as e:
            logger.error(
                f"[COMPLETE QUEST] Error generating response for profile {profile.id}: {str(e)}",
                exc_info=True,
            )
            return JsonResponse(
                {
                    "error": "An unexpected error occurred while generating the response."
                },
                status=500,
            )

    except OperationalError as e:
        # Handle database operational errors
        logger.error(
            f"[COMPLETE QUEST] Database operational error for profile {profile.id}: {str(e)}",
            exc_info=True,
        )
        return JsonResponse(
            {"error": "A database error occurred. Please try again later."}, status=500
        )
    except Exception as e:
        # Catch-all for unexpected errors
        logger.error(
            f"[COMPLETE QUEST] Error completing quest for user {profile.id}: {str(e)}",
            exc_info=True,
        )
        return JsonResponse(
            {"error": "An unexpected error occurred while completing quest"}, status=500
        )


@login_required
@csrf_exempt
def submit_bug_report(request):
    """
    Receives and processes a bug report from the user.

    :param request: The HTTP POST request containing bug report details in JSON format.
    :type request: django.http.HttpRequest
    :return: A JSON response confirming the success or failure of the report submission.
    :rtype: django.http.JsonResponse
    """
    if request.method != "POST":
        logger.warning(
            f"[SUBMIT BUG REPORT] Invalid method {request.method} used by user {request.user.profile.id}"
        )
        return JsonResponse({"error": "Invalid method"}, status=405)

    try:
        # Parse JSON data from the request
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            logger.error(f"[SUBMIT BUG REPORT] JSON decode error: {e}", exc_info=True)
            return JsonResponse(
                {"success": False, "error": "Invalid JSON format"}, status=400
            )

        logger.error(f"[SUBMIT BUG REPORT] Bug Report Received: {data}")

        # Respond with success
        return JsonResponse(
            {"success": True, "message": "Bug report submitted successfully"}
        )

    except Exception as e:
        logger.error(
            f"[SUBMIT BUG REPORT] Failed to process bug report: {e}", exc_info=True
        )
        return JsonResponse(
            {"success": False, "error": "An unexpected error occurred"}, status=500
        )
