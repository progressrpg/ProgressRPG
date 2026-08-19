from datetime import timedelta

from celery import shared_task
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone

from character.models import PlayerCharacterLink
from .models import ActivityTimer, XpModifier
from .utils import broadcast_activity_timer

DISCONNECT_TASK_CACHE_KEY = "disconnect_task:{player_id}"

# A player's websocket heartbeat ping refreshes `last_seen` (see
# WebSocketContext.tsx HEARTBEAT_INTERVAL_MS). If a connection dies without a
# clean disconnect (crash, sleep, dropped network), Channels' disconnect() may
# never fire, so TimerConsumer's grace-period auto-complete never runs. This
# threshold is this sweep's backstop.
#
# It has to be generous, because the heartbeat is driven by a setInterval in
# the player's tab and browsers throttle those aggressively once a tab is
# backgrounded — Chrome clamps a hidden tab to roughly one aligned wake-up per
# minute after 5 minutes hidden, and a sleeping laptop or locked phone stops
# them altogether. The old 90s threshold left slack for a single missed ping,
# so a player who started a timer and then switched to another window — the
# app's core use case — had their live timer auto-completed out from under
# them a few minutes later. Tolerate many consecutive missed pings instead:
# this is a guard against a dead connection accruing XP forever, not a
# presence check.
STALE_TIMER_THRESHOLD = timedelta(minutes=10)


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
def auto_complete_timer_on_disconnect(self, player_id: int):
    """
    Complete an active activity timer for a player who disconnected without
    reconnecting within the grace window. Awards XP for elapsed time.
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
    timer.complete(completion_source="auto")
    broadcast_activity_timer(timer)
    cache.delete(DISCONNECT_TASK_CACHE_KEY.format(player_id=player_id))
    return "completed"


@shared_task
def auto_complete_timers_for_stale_players():
    """
    Backstop for connections that die without a clean websocket disconnect
    (crash, sleep, dropped network) — in these cases TimerConsumer.disconnect()
    never fires, so its grace-period auto-complete never runs and an active
    timer would otherwise keep accruing XP indefinitely.

    Sweeps for active ActivityTimers belonging to players whose last_seen
    heartbeat is older than STALE_TIMER_THRESHOLD (or was never set), and
    completes them the same way the disconnect grace period does.
    """
    cutoff = timezone.now() - STALE_TIMER_THRESHOLD
    stale_timers = (
        ActivityTimer.objects.select_related("player", "activity")
        .filter(status="active")
        .filter(Q(player__last_seen__isnull=True) | Q(player__last_seen__lt=cutoff))
    )

    completed_count = 0
    for timer in stale_timers:
        truncate_to_last_heartbeat(timer)
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
