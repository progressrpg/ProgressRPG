from django.db import models
from datetime import time

from character.services import behaviour_services


class Behaviour(models.Model):
    character = models.OneToOneField(
        "character.Character", on_delete=models.CASCADE, related_name="behaviour"
    )

    DAWN_TIME = time(6, 0)
    DUSK_TIME = time(20, 0)

    def _day_window(self, date):
        """
        Return (dawn_dt, dusk_dt, next_dawn_dt) as timezone-aware datetimes in current timezone.
        """
        return behaviour_services.day_window(self, date)

    def generate_day(self, date, replace_future=True):
        """ """
        return behaviour_services.generate_day(
            self, date, replace_future=replace_future
        )

    def sync_to_now(self, now=None):
        """
        Bring the character's scheduled activities up-to-date:
        - Complete any scheduled activities whose scheduled_end <= now and not complete.
        - Ensure the current scheduled activity has started_at set to scheduled_start (optional, for display).
        - Returns the current activity (or next upcoming if none current).
        """
        return behaviour_services.sync_to_now(self, now=now)

    def advance(self, now=None):
        """
        Force-advance behaviour:
        - Complete the current scheduled activity (even if it hasn't reached scheduled_end yet)
        - Return the next scheduled activity (by scheduled_start)

        Useful if you later implement "player comes online interrupts character behaviour".
        """
        return behaviour_services.advance(self, now=now)

    def delete_day(self, date):
        return behaviour_services.delete_day(self, date)

    def get_current_activity(self):
        """
        Return the current scheduled activity (or None)
        """
        return behaviour_services.get_current_activity(self)

    def interrupt_current_activity(self, boost_ended=False):
        """
        Interrupt the current activity by completing it and starting a new instance of it.
        """
        return behaviour_services.interrupt_current_activity(
            self, boost_ended=boost_ended
        )

    def __str__(self):
        return f"Behaviour for {self.character.name}"
