from django.db import models
from django.utils import timezone
from django.db import transaction
from datetime import datetime, time, timedelta

from progression.models import CharacterActivity


class Behaviour(models.Model):
    character = models.OneToOneField(
        "character.Character", on_delete=models.CASCADE, related_name="behaviour"
    )

    DAWN_TIME = time(6, 0)
    DUSK_TIME = time(22, 0)

    def _day_window(self, date):
        """
        Return (dawn_dt, dusk_dt, next_dawn_dt) as timezone-aware datetimes in current timezone.
        """
        tz = timezone.get_current_timezone()

        dawn_naive = datetime.combine(date, self.DAWN_TIME)
        dusk_naive = datetime.combine(date, self.DUSK_TIME)
        next_dawn_naive = datetime.combine(date + timedelta(days=1), self.DAWN_TIME)

        dawn = timezone.make_aware(dawn_naive, tz)
        dusk = timezone.make_aware(dusk_naive, tz)
        next_dawn = timezone.make_aware(next_dawn_naive, tz)
        return dawn, dusk, next_dawn

    @transaction.atomic
    def generate_day(self, date, replace_future=True):
        """
        Generate 2 scheduled CharacterActivity rows for a given date:
        - day:  dawn -> dusk
        - rest: dusk -> next dawn

        If replace_future=True, deletes any *future, incomplete* scheduled activities
        that overlap this window (prevents duplicates).
        """
        dawn, dusk, next_dawn = self._day_window(date)

        qs = CharacterActivity.objects.select_for_update().filter(
            character=self.character
        )

        if replace_future:
            # delete any scheduled, not-yet-complete items that overlap this day's window
            qs.filter(
                is_complete=False,
                scheduled_start__lt=next_dawn,
                scheduled_end__gt=dawn,
            ).delete()

        day_act = CharacterActivity.objects.create(
            character=self.character,
            kind="day",
            name="",
            scheduled_start=dawn,
            scheduled_end=dusk,
            # 'dumb' record: nothing "happened" yet
            started_at=None,
            duration=0,  # also set default by model
            is_complete=False,
            complete_at=None,
            xp_gained=None,
        )

        rest_act = CharacterActivity.objects.create(
            character=self.character,
            kind="rest",
            name="",
            scheduled_start=dusk,
            scheduled_end=next_dawn,
            # 'dumb' record: nothing "happened" yet
            started_at=None,
            duration=0,
            is_complete=False,
            complete_at=None,
            xp_gained=None,
        )

        return [day_act, rest_act]

    @transaction.atomic
    def sync_to_now(self, now=None):
        """
        Bring the character's scheduled activities up-to-date:
        - Complete any scheduled activities whose scheduled_end <= now and not complete.
        - Ensure the current scheduled activity has started_at set to scheduled_start (optional, for display).
        - Returns the current activity (or next upcoming if none current).
        """
        now = now or timezone.now()

        qs = (
            CharacterActivity.objects.select_for_update()
            .filter(character=self.character)
            .exclude(scheduled_start__isnull=True)
            .exclude(scheduled_end__isnull=True)
        )

        # 1) Complete ended scheduled activities
        ended = qs.filter(is_complete=False, scheduled_end__lte=now).order_by(
            "scheduled_end"
        )
        for a in ended:
            # set what actually happened
            if a.started_at is None:
                a.started_at = a.scheduled_start

            a.duration = max(
                0, int((a.scheduled_end - a.scheduled_start).total_seconds())
            )
            a.xp_gained = a.calculate_xp_reward()

            # use scheduled_end as completion time
            a.completed_at = a.scheduled_end
            a.is_complete = True

            a.save(
                update_fields=[
                    "started_at",
                    "duration",
                    "xp_gained",
                    "completed_at",
                    "is_complete",
                ]
            )

        # 2) Current activity = schedule window containing now
        current = (
            qs.filter(scheduled_start__lte=now, scheduled_end__gt=now)
            .order_by("scheduled_start")
            .first()
        )

        if current:
            if current.started_at is None:
                current.started_at = current.scheduled_start
                current.save(update_fields=["started_at"])
            return current

        # 3) If none curent, return next upcoming (or None)
        return qs.filter(scheduled_start__gt=now).order_by("scheduled_start").first()

    def advance(self, now=None):
        """
        Force-advance behaviour:
        - Complete the current scheduled activity (even if it hasn't reached scheduled_end yet)
        - Return the next scheduled activity (by scheduled_start)

        Useful if you later implement "player comes online interrupts character behaviour".
        """
        now = now or timezone.now()

        qs = (
            CharacterActivity.objects.select_for_update()
            .filter(character=self.character)
            .exclude(scheduled_start__isnull=True)
            .exclude(scheduled_end__isnull=True)
            .order_by("scheduled_start")
        )

        current = qs.filter(scheduled_start__lte=now, scheduled_end__gt=now).first()
        if not current:
            # nothing to advance; just sync and return whatever is current/next
            return self.sync_to_now(now=now)

        if not current.is_complete:
            if current.started_at is None:
                current.started_at = current.scheduled_start

            # If you force-advance early, duration becomes "time spent so far"
            current.duration = max(0, int((now - current.started_at).total_seconds()))
            current.xp_gained = current.calculate_xp_reward()
            current.completed_at = now
            current.is_complete = True
            current.save(
                update_fields=[
                    "started_at",
                    "duration",
                    "xp_gained",
                    "completed_at",
                    "is_complete",
                ]
            )

        # Next = next scheduled by start time
        nxt = qs.filter(scheduled_start__gte=current.scheduled_end).first()
        if nxt and nxt.started_at is None and nxt.scheduled_start <= now:
            nxt.started_at = nxt.scheduled_start
            nxt.save(update_fields=["started_at"])

        return nxt

    def delete_day(self, date):
        day = self.days.filter(date=date).first()
        if not day:
            return
        day.delete_all()
        day.delete()

    def __str__(self):
        return f"Behaviour for {self.character.name}"
