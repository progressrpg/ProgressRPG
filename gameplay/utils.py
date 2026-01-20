"""
Gameplay Utility Functions

This module provides a variety of utility functions to support the gameplay application.
It handles tasks such as checking quest eligibility, managing timers, and sending WebSocket
messages to clients. These functions enhance core gameplay logic and enable real-time
communication between the server and users.

Functions:
    - check_quest_eligibility(character, profile): Checks which quests a character is eligible for based on their profile and quest history.
    - start_server_timers(act_timer, quest_timer): Asynchronously starts the server-side activity and quest timers.
    - pause_server_timers(act_timer, quest_timer): Asynchronously pauses the server-side activity and quest timers.
    - control_timers(profile, act_timer, quest_timer, mode): Asynchronously starts or pauses both server and client timers, with WebSocket feedback.
    - process_initiation(profile, character, action): Create activity or choose quest, handling timers and WebSocket updates.
    - process_completion(profile, character, action): Submits activity or completes quest, handling timers and WebSocket updates.
    - send_group_message(group_name, message): Sends a message to a WebSocket group.

Usage:
These utilities support core gameplay mechanics, such as managing quest eligibility,
handling timers, and enabling asynchronous communication via Django Channels.
They also improve the user experience by integrating real-time features and sending user notifications.

Author:
    Duncan Appleby

"""

from asgiref.sync import async_to_sync

# from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer

# from django.db import transaction, connection, IntegrityError
# from django.utils.html import escape
# from django.utils.timezone import now

from .models import QuestCompletion, Quest, ActivityTimer, QuestTimer

# from .models import ServerMessage
from .serializers import QuestTimerSerializer

# from .serializers import QuestSerializer, ActivityTimerSerializer

from character.models import Character

# from character.serializers import CharacterSerializer

from users.models import Player

# from users.serializers import ProfileSerializer

import logging

from progress_rpg.exceptions import QuestError, CharacterError, TimerError

logger = logging.getLogger("general")  # Get the logger for this module


def check_quest_eligibility(character: Character, player: Player) -> list:
    """
    Checks the eligibility of quests for a specific character and profile.

    :param character: The character instance to evaluate quests for.
    :type character: Character
    :param profile: The profile instance associated with the character.
    :type player: Player
    :return: A list of eligible quests for the given character and profile.
    """
    logger.info(
        f"[CHECK QUEST ELIGIBILITY] Checking eligibility for character {character.id} and profile {profile.id}"
    )
    char_quests = QuestCompletion.objects.filter(character=character)
    quests_done = {}
    for completion in char_quests:
        quests_done[completion.quest] = completion.times_completed
        # logger.debug(f"[CHECK QUEST ELIGIBILITY] Quest {completion.quest} completed {completion.times_completed} times")

    return [
        quest
        for quest in Quest.objects.all()
        if check_individual_quest(quest, character, profile, quests_done)
    ]


def check_individual_quest(
    quest: Quest, character: Character, player: Player, quests_done
):
    # logger.debug(f"[CHECK QUEST ELIGIBILITY] Evaluating quest: {quest}")

    return (
        quest.checkEligible(character, profile)
        and quest.not_repeating(character)
        and quest.requirements_met(quests_done)
    )


def start_server_timers(act_timer: ActivityTimer, quest_timer: QuestTimer):
    """
    Attempts to start server-side activity and quest timers.

    :param act_timer: The activity timer instance to be started.
    :type act_timer: ActivityTimer
    :param quest_timer: The quest timer instance to be started.
    :type quest_timer: QuestTimer
    :return: A tuple where the first value is a boolean indicating success,
        and the second value is a string containing additional information or error details.
    """
    logger.info("[START SERVER TIMERS] Attempting to start server timers")
    logger.debug(
        f"[START SERVER TIMERS] Timers status: activity={act_timer.status}, quest={quest_timer.status}"
    )
    qt = quest_timer
    logger.debug(
        f"[START SERVER TIMERS] Quest timer status/duration/elapsed/remaining: {qt.status}/{qt.duration}/{qt.get_elapsed_time()}/{qt.get_remaining_time()}"
    )

    if act_timer.status in ["active", "paused", "waiting"] and quest_timer.status in [
        "active",
        "paused",
        "waiting",
    ]:
        try:
            act_timer.start()
            quest_timer.start()
            result_text = "[START SERVER TIMERS] Timers successfully started"
            logger.info(result_text)
            return True, result_text
        except Exception as e:
            error_text = f"[START SERVER TIMERS] Error starting timers: {e}"
            logger.error(error_text, exc_info=True)
            return False, error_text
    else:
        result_text = f"[START SERVER TIMERS] Timers not in a valid state (activity: {act_timer.status}, quest: {quest_timer.status})"
        logger.info(result_text)
        return False, result_text


def pause_server_timers(act_timer: ActivityTimer, quest_timer: QuestTimer):
    """
    Pauses server-side activity and quest timers.

    :param act_timer: The activity timer instance to be paused.
    :type act_timer: ActivityTimer
    :param quest_timer: The quest timer instance to be paused.
    :type quest_timer: QuestTimer
    :return: A tuple where the first value is a boolean indicating success,
        and the second value is a string containing additional information or error details.
    """
    logger.info("[PAUSE SERVER TIMERS] Pausing server timers")
    logger.debug(
        f"[PAUSE SERVER TIMERS] Timers status before: {act_timer.status}/{quest_timer.status}"
    )
    qt = quest_timer
    logger.debug(
        f"[PAUSE SERVER TIMERS] Quest timer status/duration/elapsed/remaining: {qt.status}/{qt.duration}/{qt.get_elapsed_time()}/{qt.get_remaining_time()}"
    )
    try:
        if act_timer.status not in ["completed", "empty"]:
            act_timer.pause()
            logger.debug("[PAUSE SERVER TIMERS] Activity timer successfully paused")
        else:
            result_text = f"[PAUSE SERVER TIMERS] Activity timer NOT paused, status: {act_timer.status}"
            logger.debug(result_text)

        if quest_timer.status not in ["completed", "empty"]:
            quest_timer.pause()
            logger.debug("[PAUSE SERVER TIMERS] Quest timer successfully paused")
        else:
            logger.debug(
                f"[PAUSE SERVER TIMERS] Quest timer NOT paused, status: {act_timer.status}"
            )

        # logger.debug("[PAUSE SERVER TIMERS] Timers paused (or status is complete/empty)")
        logger.debug(
            f"[PAUSE SERVER TIMERS] Timers status after pausing: {act_timer.status}/{quest_timer.status}"
        )

        return True, "Success"
    except Exception as e:
        result_text = f"[PAUSE SERVER TIMERS] Error pausing timers: {e}"
        logger.error(result_text, exc_info=True)
        return False, result_text


async def control_timers(
    player: Player, act_timer: ActivityTimer, quest_timer: QuestTimer, mode: str
) -> bool:
    """
    Starts or pauses timers for a specific profile by controlling server-side timers.

    :param profile: The profile the timers.
    :type player: Player
    :param act_timer: The activity timer instance.
    :type act_timer: ActivityTimer
    :param quest_timer: The quest timer instance.
    :type quest_timer: QuestTimer
    :param mode: Should be "start" or "pause".
    :type mode: str
    :return: True if success, otherwise False.
    """
    profile_id = profile.id
    logger.info(
        f"[CONTROL TIMERS] Performing '{mode}' on timers for profile {profile_id}"
    )
    qt = quest_timer
    logger.debug(
        f"[CONTROL TIMERS] Quest timer status/duration/elapsed/remaining: {qt.status}/{qt.duration}/{qt.get_elapsed_time()}/{qt.get_remaining_time()}"
    )
    if mode == "start":
        server_success, result_text = await database_sync_to_async(start_server_timers)(
            act_timer, quest_timer
        )
        action = "start_timers"
        success_message = "Timers successfully started"
        failure_message = "Starting timers failed"
    elif mode == "pause":
        server_success, result_text = await database_sync_to_async(pause_server_timers)(
            act_timer, quest_timer
        )
        action = "pause_timers"
        success_message = "Timers successfully paused"
        failure_message = "Pausing timers failed"
    else:
        result_text = f"[CONTROL TIMERS] Invalid mode: {mode}"
        logger.warning(result_text)

    if server_success:
        logger.info(f"[CONTROL TIMERS] {success_message} for profile {profile_id}")
        await send_group_message(
            f"profile_{profile_id}",
            {"type": "action", "action": action, "success": True},
        )
        return True
    else:
        logger.warning(f"[CONTROL TIMERS] {failure_message} for profile {profile_id}")
        await send_group_message(
            f"profile_{profile_id}",
            {
                "type": "response",
                "action": "console.log",
                "message": result_text,
            },
        )
        return False


def server_quest_ready(quest_timer: QuestTimer) -> bool:
    """
    Checks if server quest timer is (nearly) complete.
    :param quest_timer: Quest timer
    :type quest_timer: QuestTimer
    :return: True if the quest is nearly complete, False otherwise
    :rtype: bool
    """
    if not quest_timer.status == "complete":
        if quest_timer.get_remaining_time() >= 4:
            return False
        else:
            return True


def process_initiation(player: Player, character: Character, action: str) -> bool:
    """
    Processes the initiation of an activity or quest, starting timers if possible.

    :param profile: The profile associated with the quest.
    :type player: Player
    :param character: The character instance completing the quest.
    :type character: Character
    :param action: The action being performed (e.g., "create_activity" or "choose_quest").
    :type action: str
    :return: True if the quest is successfully completed, False otherwise.
    :rtype: bool
    """
    profile.refresh_from_db()
    profile_id = profile.id
    act_timer = profile.activity_timer
    character.refresh_from_db()
    quest_timer = character.quest_timer
    logger.info(
        f"[PROCESS INITIATION] Initiating {action} for profile {profile_id}, character {character.id}"
    )
    # logger.debug(f"[PROCESS INITIATION] Timers status: {act_timer.status}/{quest_timer.status}")
    qt = quest_timer
    # logger.debug(f"[PROCESS INITIATION] Quest timer after refresh status/duration/elapsed/remaining: {qt.status}/{qt.duration}/{qt.get_elapsed_time()}/{qt.get_remaining_time()}")

    start_success, result_text = start_server_timers(act_timer, quest_timer)
    if not start_success:
        logger.info(
            f"[PROCESS INITIATION] Failed to start timers for profile {profile_id}. Result: {result_text}"
        )
        async_to_sync(send_group_message)(
            f"profile_{profile_id}",
            {"type": "response", "action": "console.log", "message": result_text},
        )
        return False
    else:  # Success
        # act_timer.refresh_from_db()
        # quest_timer.refresh_from_db()
        async_to_sync(send_group_message)(
            f"profile_{profile_id}",
            {
                "type": "action",
                "action": (
                    "create_activity" if action == "create_activity" else "choose_quest"
                ),
            },
        )
        return True


def process_completion(player: Player, character: Character, action: str) -> bool:
    """
    Processes the completion of an activity or quest, pausing timers.

    :param profile: The profile associated with the quest.
    :type player: Player
    :param character: The character instance completing the quest.
    :type character: Character
    :param action: The action being performed (e.g., "quest_complete" or "submit_activity").
    :type action: str
    :return: True if the quest is successfully completed, False otherwise.
    :rtype: bool
    """
    profile.refresh_from_db()
    character.refresh_from_db()
    profile_id = profile.id
    act_timer = profile.activity_timer
    quest_timer = character.quest_timer
    logger.info(
        f"[PROCESS COMPLETION] Doing {action} for profile {profile_id}, character {character.id}"
    )

    if action == "complete_quest":
        ready = server_quest_ready(quest_timer)
        logger.info(f"[PROCESS COMPLETION] Ready is: {ready}")
    else:
        ready = True

    if ready:
        pause_success, result_text = pause_server_timers(act_timer, quest_timer)
        if not pause_success:
            logger.warning(
                f"[PROCESS COMPLETION] Failed to pause timers for profile {profile_id}"
            )
            async_to_sync(send_group_message)(
                f"profile_{profile_id}",
                {"type": "error", "action": "warn", "message": "Pausing timers failed"},
            )
            return False
        else:  # Success
            # act_timer.refresh_from_db()
            # quest_timer.refresh_from_db()
            async_to_sync(send_group_message)(
                f"profile_{profile_id}",
                {
                    "type": "action",
                    "action": (
                        "quest_complete"
                        if action == "complete_quest"
                        else "submit_activity"
                    ),
                },
            )
            return True

    else:  # Quest timer not near enough to completion
        logger.warning(f"[PROCESS COMPLETION] Quest not ready for completion")
        serialized_timer = QuestTimerSerializer(quest_timer).data
        async_to_sync(send_group_message)(
            f"profile_{profile_id}",
            {
                "success": True,
                "type": "action",
                "action": "correct_quest_timer",
                "data": serialized_timer,
            },
        )
        return False


async def send_group_message(group_name: str, message: dict) -> bool:
    logger.info(
        f"[SEND GROUP MESSAGE] Sending message to group {group_name}. Message: {message}"
    )
    # logger.debug(f"[SEND GROUP MESSAGE] Sending message to group {group_name}. Message type: {message.get('type')}, action: {message.get('action')}, message: {message.get('message')}\ndata: {message.get('data')}\n")
    # logger.debug(f"[SEND GROUP MESSAGE] Type of message argument: {type(message)}")
    if message.get("type") in ["event", "notification", "response"]:
        logger.debug("[SEND GROUP MESSAGE] Wrapping message in 'server message' type")
        message = {"type": "server_message", "data": message}
    elif message.get("type") == "action":
        logger.debug(
            f"[SEND GROUP MESSAGE] Action type. Message instance type: {type(message)}"
        )

    channel_layer = get_channel_layer()
    # logger.info(f"[SEND GROUP MESSAGE] Channel layer: {channel_layer}")
    if channel_layer is not None:
        try:
            await channel_layer.group_send(group_name, message)
            logger.debug(
                f"[SEND GROUP MESSAGE] Data sent to group '{group_name}': {message}"
            )
            return True
        except ConnectionError as e:
            logger.error(
                f"[SEND GROUP MESSAGE] Connection error sending data to group '{group_name}': {e}"
            )
        except ValueError as e:
            logger.error(
                f"[SEND GROUP MESSAGE] Value error in message format for group '{group_name}': {e}"
            )
        except Exception as e:
            logger.exception(
                f"[SEND GROUP MESSAGE] Unexpected error sending to group '{group_name}': {e}"
            )
        return False
    else:
        logger.warning(
            f"[GROUP SEND MESSAGE] No channel layer available for group '{group_name}'"
        )
        return False


def validate_quest_completion(character):
    """Validate that a quest can be completed"""
    if not hasattr(character, 'quest_timer') or not character.quest_timer:
        raise CharacterError("Character has no quest timer")
    
    quest = character.quest_timer.quest
    if not quest:
        raise QuestError("No active quest to complete")
    
    if character.quest_timer.status != "completed":
        raise TimerError(f"Quest timer is not completed (status: {character.quest_timer.status})")
    
    return quest
