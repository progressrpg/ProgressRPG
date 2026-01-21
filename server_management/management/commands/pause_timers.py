from django.core.management.base import BaseCommand
from django.utils import timezone
from gameplay.models import ActivityTimer, QuestTimer
import logging

logger = logging.getLogger("general")


class Command(BaseCommand):
    help = "Pauses all active server timers during maintenance"

    def handle(self, *args, **kwargs):
        active_act_timers = ActivityTimer.objects.filter(status="Active")
        for timer in active_act_timers:
            timer.pause()

        active_quest_timers = QuestTimer.objects.filter(status="Active")
        for timer in active_quest_timers:
            timer.pause()

        logger.info(
            f"[COMMAND: PAUSE ALL TIMERS] {active_act_timers.count()} active Activity timers paused; {active_quest_timers.count()} active Quest timers paused."
        )
