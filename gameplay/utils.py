"""
Gameplay Utility Functions

This module provides a variety of utility functions to support the gameplay application.
It handles tasks such as managing timers and sending WebSocket messages to clients.
These functions enhance core gameplay logic and enable real-time communication
between the server and users.

Functions:
    - start_server_timers(act_timer): Asynchronously starts the server-side activity timer.
    - pause_server_timers(act_timer): Asynchronously pauses the server-side activity timer.
    - control_timers(player, act_timer, mode): Asynchronously starts or pauses both server and client timers, with WebSocket feedback.
    - process_initiation(player, character, action): Create an activity, handling timers and WebSocket updates.
    - process_completion(player, character, action): Submits an activity, handling timers and WebSocket updates.
    - send_group_message(group_name, message): Sends a message to a WebSocket group.

Usage:
These utilities support core gameplay mechanics, such as handling timers and
enabling asynchronous communication via Django Channels. They also improve the
user experience by integrating real-time features and sending user notifications.

Author:
    Duncan Appleby

"""

from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer

from .models import ActivityTimer

from character.models import Character
from users.models import Player

import logging

logger = logging.getLogger("general")


def start_server_timers(act_timer: ActivityTimer):
    """
    Attempts to start the server-side activity timer.
    """
    logger.info("[START SERVER TIMERS] Attempting to start server timers")
    logger.debug(f"[START SERVER TIMERS] Timers status: activity={act_timer.status}")

    if act_timer.status in [
        ActivityTimer.Status.ACTIVE,
        ActivityTimer.Status.PAUSED,
        ActivityTimer.Status.WAITING,
    ]:
        try:
            from gameplay.services.xp_modifiers import set_activity_active_modifiers

            act_timer.start()
            set_activity_active_modifiers(act_timer.player, is_active=True)
            result_text = "[START SERVER TIMERS] Timers successfully started"
            logger.info(result_text)
            return True, result_text
        except Exception as e:
            error_text = f"[START SERVER TIMERS] Error starting timers: {e}"
            logger.error(error_text, exc_info=True)
            return False, error_text
    else:
        result_text = f"[START SERVER TIMERS] Timers not in a valid state (activity: {act_timer.status})"
        logger.info(result_text)
        return False, result_text


def pause_server_timers(act_timer: ActivityTimer):
    """
    Pauses the server-side activity timer.
    """
    logger.info("[PAUSE SERVER TIMERS] Pausing server timers")
    logger.debug(f"[PAUSE SERVER TIMERS] Timers status before: {act_timer.status}")

    try:
        if act_timer.status not in [
            ActivityTimer.Status.COMPLETED,
            ActivityTimer.Status.EMPTY,
        ]:
            from gameplay.services.xp_modifiers import set_activity_active_modifiers

            act_timer.pause()
            set_activity_active_modifiers(act_timer.player, is_active=False)
            logger.debug("[PAUSE SERVER TIMERS] Activity timer successfully paused")
        else:
            result_text = f"[PAUSE SERVER TIMERS] Activity timer NOT paused, status: {act_timer.status}"
            logger.debug(result_text)

        logger.debug(
            f"[PAUSE SERVER TIMERS] Timers status after pausing: {act_timer.status}"
        )

        return True, "Success"
    except Exception as e:
        result_text = f"[PAUSE SERVER TIMERS] Error pausing timers: {e}"
        logger.error(result_text, exc_info=True)
        return False, result_text


async def control_timers(player: Player, act_timer: ActivityTimer, mode: str) -> bool:
    """
    Starts or pauses timers for a specific player by controlling server-side timers.

    """
    player_id = player.id
    logger.info(
        f"[CONTROL TIMERS] Performing '{mode}' on timers for player {player_id}"
    )

    if mode == "start":
        server_success, result_text = await database_sync_to_async(start_server_timers)(
            act_timer
        )
        action = "start_timers"
        success_message = "Timers successfully started"
        failure_message = "Starting timers failed"
    elif mode == "pause":
        server_success, result_text = await database_sync_to_async(pause_server_timers)(
            act_timer
        )
        action = "pause_timers"
        success_message = "Timers successfully paused"
        failure_message = "Pausing timers failed"
    else:
        # Returns rather than falling through: the branches above are what
        # assign `server_success`/`action`/the log messages, so continuing
        # past here would read an unbound local. Mirrors the failure
        # contract of the two valid modes - a caller in an async consumer
        # gets False, not an exception.
        result_text = f"[CONTROL TIMERS] Invalid mode: {mode}"
        logger.warning(result_text)
        await send_group_message(
            f"player_{player_id}",
            {
                "type": "response",
                "action": "console.log",
                "message": result_text,
            },
        )
        return False

    if server_success:
        logger.info(f"[CONTROL TIMERS] {success_message} for player {player_id}")
        await send_group_message(
            f"player_{player_id}",
            {"type": "action", "action": action, "success": True},
        )
        return True
    else:
        logger.warning(f"[CONTROL TIMERS] {failure_message} for player {player_id}")
        await send_group_message(
            f"player_{player_id}",
            {
                "type": "response",
                "action": "console.log",
                "message": result_text,
            },
        )
        return False


def process_initiation(player: Player, character: Character, action: str) -> bool:
    """
    Processes the initiation of an activity, starting timers if possible.
    """
    player.refresh_from_db()
    player_id = player.id
    act_timer = player.activity_timer
    character.refresh_from_db()
    logger.info(
        f"[PROCESS INITIATION] Initiating {action} for player {player_id}, character {character.id}"
    )

    start_success, result_text = start_server_timers(act_timer)
    if not start_success:
        logger.info(
            f"[PROCESS INITIATION] Failed to start timers for player {player_id}. Result: {result_text}"
        )
        async_to_sync(send_group_message)(
            f"player_{player_id}",
            {"type": "response", "action": "console.log", "message": result_text},
        )
        return False
    else:  # Success
        async_to_sync(send_group_message)(
            f"player_{player_id}",
            {
                "type": "action",
                "action": "create_activity",
            },
        )
        return True


def process_completion(player: Player, character: Character, action: str) -> bool:
    """
    Processes the completion of an activity, pausing timers.
    """
    player.refresh_from_db()
    character.refresh_from_db()
    player_id = player.id
    act_timer = player.activity_timer
    logger.info(
        f"[PROCESS COMPLETION] Doing {action} for player {player_id}, character {character.id}"
    )

    pause_success, result_text = pause_server_timers(act_timer)
    if not pause_success:
        logger.warning(
            f"[PROCESS COMPLETION] Failed to pause timers for player {player_id}"
        )
        async_to_sync(send_group_message)(
            f"player_{player_id}",
            {"type": "error", "action": "warn", "message": "Pausing timers failed"},
        )
        return False
    else:
        async_to_sync(send_group_message)(
            f"player_{player_id}",
            {
                "type": "action",
                "action": "submit_activity",
            },
        )
        return True


def broadcast_activity_timer(timer: ActivityTimer) -> None:
    """
    Push `timer`'s current state to every other open session (tabs, devices)
    this player has connected, so they can reconcile via useActivityTimer's
    loadFromServer instead of drifting until their next manual fetch.
    Reuses the per-player `player_{id}` group that TimerConsumer already
    joins on connect. Safe to call from sync contexts (views, Celery tasks).
    """
    from .serializers import ActivityTimerSerializer

    async_to_sync(send_group_message)(
        f"player_{timer.player_id}",
        {
            "type": "action",
            "action": "activity_timer_update",
            "data": {"activity_timer": ActivityTimerSerializer(timer).data},
        },
    )


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
