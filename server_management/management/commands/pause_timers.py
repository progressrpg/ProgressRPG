from django.core.management.base import BaseCommand
from django.utils import timezone
from gameplay.models import ActivityTimer
from gameplay.utils import pause_server_timers
import logging

logger = logging.getLogger("general")


class Command(BaseCommand):
    help = "Pauses all active server timers during maintenance"

    def handle(self, *args, **kwargs):
        # "active", not "Active" - the stored value is lowercase, so this
        # filter matched nothing and maintenance mode has been pausing no
        # timers at all. Counted before pausing, since the queryset no
        # longer matches them afterwards.
        active_act_timers = list(ActivityTimer.objects.filter(status="active"))
        for timer in active_act_timers:
            pause_server_timers(timer)

        logger.info(
            f"[COMMAND: PAUSE ALL TIMERS] {len(active_act_timers)} active Activity timers paused."
        )
