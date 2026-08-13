from datetime import timedelta

from celery import shared_task
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone

from character.models import PlayerCharacterLink
from .models import XpModifier
from .utils import broadcast_activity_timer

DISCONNECT_TASK_CACHE_KEY = "disconnect_task:{player_id}"

# A player's websocket heartbeat ping refreshes `last_seen` every 60s
# (see WebSocketContext.tsx HEARTBEAT_INTERVAL_MS). If a connection dies
# without a clean disconnect (crash, sleep, dropped network), Channels'
# disconnect() may never fire, so TimerConsumer's grace-period auto-complete
# never runs. This threshold is this sweep's backstop: 1.5x the ping
# interval tolerates one missed ping before treating a timer as abandoned.
STALE_TIMER_THRESHOLD = timedelta(seconds=90)


@shared_task(bind=True)
def auto_complete_timer_on_disconnect(self, player_id: int):
    """
    Complete an active activity timer for a player who disconnected without
    reconnecting within the grace window. Awards XP for elapsed time.
    Revoked by TimerConsumer.connect() if the player reconnects in time.
    """
    from .models import ActivityTimer

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

    timer.complete(completion_source="auto")
    broadcast_activity_timer(timer)
    cache.delete(DISCONNECT_TASK_CACHE_KEY.format(player_id=player_id))
    return "completed"


@shared_task
def auto_complete_timers_for_stale_players():
    """
    Backstop for connections that die without a clean websocket disconnect
    (crash, sleep, dropped network) — in these cases TimerConsumer.disconnect()
    never fires, so its 30s grace-period auto-complete never runs and an
    active timer would otherwise keep accruing XP indefinitely.

    Sweeps for active ActivityTimers belonging to players whose last_seen
    heartbeat is older than STALE_TIMER_THRESHOLD (or was never set), and
    completes them the same way the disconnect grace period does.
    """
    from .models import ActivityTimer

    cutoff = timezone.now() - STALE_TIMER_THRESHOLD
    stale_timers = (
        ActivityTimer.objects.select_related("player", "activity")
        .filter(status="active")
        .filter(Q(player__last_seen__isnull=True) | Q(player__last_seen__lt=cutoff))
    )

    completed_count = 0
    for timer in stale_timers:
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
