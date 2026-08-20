from datetime import timedelta

from celery import shared_task
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone

from character.models import PlayerCharacterLink
from .models import ActivityTimer, XpModifier
from .utils import broadcast_activity_timer, pause_server_timers

# How long a paused session is left for the player to resolve before it is
# closed out on their behalf. ActivityTimer is OneToOne with Player and
# set_activity refuses to start a new session over banked time, so an
# unresolved pause blocks starting anything else - this is the safety valve
# if the UI ever fails to offer the choice. It completes rather than
# discards: the work was real, so it is credited to the day it happened on,
# just later than the player would have done it themselves.
ABANDONED_PAUSE_HORIZON = timedelta(days=7)

DISCONNECT_TASK_CACHE_KEY = "disconnect_task:{player_id}"

# `last_seen` is stamped by TimerConsumer for as long as it holds an open
# socket (see consumers.HEARTBEAT_INTERVAL_SECONDS, 60s). If the process
# dies without a clean disconnect - OOM, crash, deploy restart - the stamps
# simply stop, and TimerConsumer.disconnect() never runs to pause the timer.
# This sweep is the backstop for exactly that case.
#
# It can be tight now that the signal is server-side. It used to be driven
# by a setInterval in the player's tab, which browsers throttle when the tab
# is backgrounded and stop when the device sleeps, so the threshold had to
# absorb a browser's scheduling rather than a process's liveness. Four
# minutes tolerates three consecutive missed stamps, which for an in-process
# loop means the worker is wedged, not that the player stepped away.
STALE_TIMER_THRESHOLD = timedelta(minutes=4)


def truncate_to_last_heartbeat(timer: ActivityTimer) -> None:
    """
    Bank `timer`'s elapsed time up to the player's last confirmed heartbeat
    before an auto-complete awards XP for it.

    Timer.complete() credits everything up to `now()`, so without this an
    auto-complete would also award the whole window we spent waiting to decide
    the session was gone. Crediting only up to `last_seen` keeps that window
    free to be as generous as it needs to be (see STALE_TIMER_THRESHOLD) —
    waiting longer before giving up on a player can no longer inflate the XP
    they're awarded when we do.

    No-op when the heartbeat predates the current run (or is missing), in which
    case there is no evidence of time worked beyond what's already banked.
    """
    last_seen = timer.player.last_seen
    if not last_seen or not timer.start_time or last_seen <= timer.start_time:
        return

    timer.elapsed_time += int((last_seen - timer.start_time).total_seconds())
    timer.start_time = None
    timer.save(update_fields=["elapsed_time", "start_time"])


@shared_task(bind=True)
def auto_pause_timer_on_disconnect(self, player_id: int):
    """
    Pause an active activity timer for a player who disconnected without
    reconnecting within the grace window.

    Pausing rather than completing is the whole point: the server is
    guessing that the player is gone, and a wrong guess should cost them a
    click rather than force-submitting a session they were in the middle
    of. The banked time is theirs to resume or submit when they return.

    Revoked by TimerConsumer.connect() if the player reconnects in time.
    """
    stored_task_id = cache.get(DISCONNECT_TASK_CACHE_KEY.format(player_id=player_id))
    if stored_task_id != self.request.id:
        return "superseded"

    try:
        timer = ActivityTimer.objects.select_related("player", "activity").get(
            player_id=player_id
        )
    except ActivityTimer.DoesNotExist:
        return "no_timer"

    if timer.status != "active":
        cache.delete(DISCONNECT_TASK_CACHE_KEY.format(player_id=player_id))
        return f"skipped:{timer.status}"

    if timer.is_bounded():
        # A declared duration answers the question this task exists to ask.
        # The session has a knowable end; let it run to that end rather than
        # closing it early because the player's socket went away.
        cache.delete(DISCONNECT_TASK_CACHE_KEY.format(player_id=player_id))
        return "bounded"

    if timer.player.active_connections > 0:
        # The player still has a live socket, so this disconnect didn't end
        # their session and their timer is very much still running.
        #
        # TimerConsumer.connect() revokes this task, but only for the session
        # that reconnects. It can't cover a player who had two tabs open and
        # closed one, or whose reconnect raced ahead of the old socket's
        # disconnect — in both cases nothing runs connect() afterwards, so
        # this task would survive to auto-complete a timer the player is
        # watching tick in another window. Their remaining connection is
        # the answer: don't close out a session that's still here.
        cache.delete(DISCONNECT_TASK_CACHE_KEY.format(player_id=player_id))
        return "still_connected"

    truncate_to_last_heartbeat(timer)
    # pause_server_timers rather than timer.pause(): it also deactivates the
    # player's activity XP modifiers, which would otherwise keep running
    # against a session that has stopped.
    pause_server_timers(timer)
    broadcast_activity_timer(timer)
    cache.delete(DISCONNECT_TASK_CACHE_KEY.format(player_id=player_id))
    return "paused"


@shared_task
def auto_pause_timers_for_stale_players():
    """
    Backstop for connections that die without a clean websocket disconnect
    (crash, sleep, dropped network) — in these cases TimerConsumer.disconnect()
    never fires, so its grace-period pause never runs and an active timer
    would otherwise keep accruing XP indefinitely.

    Sweeps for active ActivityTimers belonging to players whose last_seen
    heartbeat is older than STALE_TIMER_THRESHOLD (or was never set), and
    pauses them the same way the disconnect grace period does.
    """
    cutoff = timezone.now() - STALE_TIMER_THRESHOLD
    stale_timers = (
        ActivityTimer.objects.select_related("player", "activity")
        .filter(status="active")
        # Bounded sessions are excluded: they declared their own end, so
        # complete_expired_bounded_timers closes them out at that end
        # instead of this sweep guessing from a heartbeat.
        .filter(Q(limit_seconds__isnull=True) | Q(limit_seconds=0))
        .filter(Q(player__last_seen__isnull=True) | Q(player__last_seen__lt=cutoff))
    )

    paused_count = 0
    for timer in stale_timers:
        truncate_to_last_heartbeat(timer)
        pause_server_timers(timer)
        broadcast_activity_timer(timer)
        paused_count += 1

    return paused_count


@shared_task
def complete_abandoned_paused_timers():
    """
    Close out paused sessions the player never came back to resolve.

    Completes rather than discards, crediting the session's original logical
    day: the work was real, so this delays the XP rather than losing it.
    """
    cutoff = timezone.now() - ABANDONED_PAUSE_HORIZON

    abandoned = ActivityTimer.objects.select_related("player", "activity").filter(
        status="paused", elapsed_time__gt=0, last_updated__lt=cutoff
    )

    completed_count = 0
    for timer in abandoned:
        timer.complete(completion_source="auto")
        broadcast_activity_timer(timer)
        completed_count += 1

    return completed_count


@shared_task
def complete_expired_bounded_timers():
    """
    Complete sessions that have run out their declared duration.

    This is what lets a bounded session keep running while the player is
    away from the device: because the end was declared up front, no verdict
    about their presence is needed - the session simply completes when it
    reaches the duration they asked for.

    Crediting differs from the unbounded paths deliberately. There we bank
    time up to the last confirmed heartbeat, because that is the last
    moment we know the player was there. Here the player declared 45
    minutes, so they get 45 minutes.
    """
    completed_count = 0

    bounded_timers = (
        ActivityTimer.objects.select_related("player", "activity")
        .filter(status="active", limit_seconds__isnull=False)
        .exclude(limit_seconds=0)
    )
    for timer in bounded_timers:
        if not timer.limit_reached():
            continue

        timer.elapsed_time = timer.limit_seconds
        timer.start_time = None
        timer.save(update_fields=["elapsed_time", "start_time"])

        timer.complete(completion_source="auto")
        broadcast_activity_timer(timer)
        completed_count += 1

    return completed_count


@shared_task(bind=True)
def end_online_boost(self, modifier_id: int):
    now = timezone.now()
    mod = XpModifier.objects.select_related("character__behaviour").get(id=modifier_id)

    # Superseded / cancelled
    if mod.task_id != self.request.id:
        return "superseded"
    if mod.ends_at is None or mod.ends_at > now or not mod.is_active:
        return "cancelled"

    # End + side effects
    mod.is_active = False
    mod.task_id = None
    mod.ends_at = now
    mod.save(update_fields=["is_active", "task_id", "ends_at"])

    behaviour = getattr(mod.character, "behaviour", None)
    if behaviour:
        behaviour.interrupt_current_activity()
    return "ended"
