from django.db import models
from django.utils import timezone
from django.db import transaction
from datetime import datetime, time, timedelta

from character.models import PlayerCharacterLink
from progression.models import CharacterActivity

import random


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
        """ """
        tz = timezone.get_current_timezone()

        rng = random.Random(f"{self.character_id}-{date.isoformat()}")

        def aware(dt_date, t: time):
            return timezone.make_aware(datetime.combine(dt_date, t), tz)

        def jitter_minutes(base_dt, minutes):
            return base_dt + timedelta(minutes=rng.randint(-minutes, minutes))

        # ---- anchors (base times) ----
        sleep_start = aware(date, time(23, 0))
        wake = aware(date, time(7, 0))
        wake = jitter_minutes(wake, 15)

        morning_start = wake
        morning_end = morning_start + timedelta(hours=1)

        work1_start = morning_end
        work1_end = aware(date, time(12, 0))

        lunch_start = work1_end
        lunch_start = jitter_minutes(lunch_start, 10)
        lunch_end = lunch_start + timedelta(hours=1)

        work2_start = lunch_end
        work2_end = aware(date, time(17, 0))

        dinner_start = aware(date, time(17, 30))
        dinner_start = jitter_minutes(dinner_start, 10)
        dinner_end = dinner_start + timedelta(hours=1)

        leisure_start = dinner_end
        leisure_end = aware(date, time(22, 30))

        wind_start = leisure_end
        wind_end = aware(date, time(23, 0))

        dawn, dusk, next_dawn = self._day_window(date)

        # Sleep spans to next day wake
        next_day = date + timedelta(days=1)
        next_wake = aware(next_day, time(7, 0))
        next_wake = jitter_minutes(next_wake, 15)

        # Sleep block for "night starting today" = 23:00 today -> 07:00 tomorrow
        sleep_start = aware(date, time(23, 0))
        sleep_end = next_wake

        blocks = [
            (
                "sleep",
                "Sleep",
                aware(date, time(0, 0)),
                morning_start,
            ),  # midnight -> wake
            ("morning", "Waking up", morning_start, morning_end),
            ("work", "Working", work1_start, work1_end),
            ("meal", "Eating lunch", lunch_start, lunch_end),
            ("work", "Working", work2_start, work2_end),
            ("meal", "Eating dinner", dinner_start, dinner_end),
            ("leisure", "Relaxing", leisure_start, leisure_end),
            ("wind_down", "Wind down", wind_start, wind_end),
            ("sleep", "Sleeping", sleep_start, sleep_end),
        ]

        # Ensure monotonic, no negative durations, no overlaps
        cleaned = []
        last_end = None
        for kind, name, start, end in blocks:
            if end <= start:
                continue
            if last_end and start < last_end:
                start = last_end
                if end <= start:
                    continue
            cleaned.append((kind, name, start, end))
            last_end = end

        qs = CharacterActivity.objects.select_for_update().filter(
            character=self.character
        )

        if replace_future:
            # delete future/incomplete activities that overlap this day's window (00:00 -> 23:59 and the sleep tail)
            window_start = aware(date, time(0, 0))
            window_end = aware(date, time(23, 59, 59))
            qs.filter(
                is_complete=False,
                scheduled_start__lt=sleep_end,
                scheduled_end__gt=window_start,
            ).delete()

        created = []
        today = timezone.now().date()
        is_past = date < today

        for kind, name, start, end in cleaned:
            activity_kwargs = {
                "character": self.character,
                "kind": kind,
                "name": name,
                "scheduled_start": start,
                "scheduled_end": end,
            }
            if is_past:
                activity_kwargs.update(
                    {
                        "is_complete": True,
                        "started_at": start,
                        "completed_at": end,
                        "duration": int((end - start).total_seconds()),
                        # Optionally: "xp_gained": <calculate or default>
                    }
                )
            created.append(CharacterActivity.objects.create(**activity_kwargs))

        return created

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
        for activity in ended:
            activity.complete_past()

        # 2) Current activity = schedule window containing now
        current = self.get_current_activity()

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

    def get_current_activity(self):
        """
        Return the current scheduled activity (or None)
        """
        now = timezone.now()
        activity = (
            CharacterActivity.objects.filter(
                character=self.character,
                scheduled_start__lte=now,
                scheduled_end__gt=now,
            )
            .order_by("scheduled_start")
            .first()
        )
        if not activity:
            return None

        return activity

    def interrupt_current_activity(self, boost_ended=False):
        """
        Interrupt the current activity by completing it and starting a new instance of it.
        """
        link = PlayerCharacterLink.objects.filter(
            character=self.character, is_active=True
        ).first()
        if not link:
            print("No active player link: no interrupt.")
            return None
        if not link.is_new_login():
            print("Not new login: no interrupt")
            return None
        print("Interrupting current activity.")
        now = timezone.now()
        activity = self.get_current_activity()
        if not activity or activity.is_complete:
            return None

        new_activity = CharacterActivity.objects.create(
            character=self.character,
            kind=activity.kind,
            name=activity.name,
            scheduled_end=activity.scheduled_end,
        )
        activity.complete_now()

        new_activity.started_at = now
        new_activity.save(update_fields=["started_at"])
        return new_activity

    def __str__(self):
        return f"Behaviour for {self.character.name}"
