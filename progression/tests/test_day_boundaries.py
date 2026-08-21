"""
Tests for logical days - the player's own day boundary, replacing the
server's calendar day.

A player's day starts at their `day_start_time` (default 02:00) in their own
timezone, and is named for the calendar date it starts on. So a session at
23:00 on Tuesday and one at 01:00 on Wednesday belong to the same day:
Tuesday.
"""

from datetime import date, datetime, time, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from django.test import TestCase
from django.utils import timezone

from gameplay.models import ActivityTimer
from progression.day_boundaries import (
    DEFAULT_DAY_START,
    current_logical_date,
    day_settings,
    logical_date_for,
    logical_day_bounds,
)
from progression.models import PlayerActivity
from users.models import UserLogin
from users.tests import user_factory

UTC = ZoneInfo("UTC")
LONDON = ZoneInfo("Europe/London")
NEW_YORK = ZoneInfo("America/New_York")


def at(tz, y, m, d, hh, mm=0):
    return datetime(y, m, d, hh, mm, tzinfo=tz)


class LogicalDateForTests(TestCase):
    def setUp(self):
        self.user = user_factory(with_player=True, timezone="Europe/London")
        self.player = self.user.player

    def test_before_the_cutoff_belongs_to_the_previous_day(self):
        self.assertEqual(
            logical_date_for(self.user, at(LONDON, 2026, 3, 4, 1, 59)),
            date(2026, 3, 3),
        )

    def test_after_the_cutoff_belongs_to_the_same_day(self):
        self.assertEqual(
            logical_date_for(self.user, at(LONDON, 2026, 3, 4, 2, 1)),
            date(2026, 3, 4),
        )

    def test_the_cutoff_instant_itself_starts_the_new_day(self):
        self.assertEqual(
            logical_date_for(self.user, at(LONDON, 2026, 3, 4, 2, 0)),
            date(2026, 3, 4),
        )

    def test_late_evening_and_the_small_hours_are_the_same_day(self):
        """The whole point: Tuesday 23:00 and Wednesday 01:00 are Tuesday."""
        tuesday_night = logical_date_for(self.user, at(LONDON, 2026, 3, 3, 23, 0))
        wednesday_small_hours = logical_date_for(
            self.user, at(LONDON, 2026, 3, 4, 1, 0)
        )

        self.assertEqual(tuesday_night, date(2026, 3, 3))
        self.assertEqual(wednesday_small_hours, tuesday_night)

    def test_uses_the_players_own_timezone(self):
        ny_user = user_factory(with_player=True, timezone="America/New_York")

        # 03:00 UTC on the 4th is 22:00 on the 3rd in New York, so it is
        # still the 3rd there - and after that day's 02:00 cutoff.
        moment = at(ZoneInfo("UTC"), 2026, 3, 4, 3, 0)

        self.assertEqual(logical_date_for(ny_user, moment), date(2026, 3, 3))
        self.assertEqual(logical_date_for(self.user, moment), date(2026, 3, 4))

    def test_honours_a_custom_day_start_time(self):
        self.user.day_start_time = time(6, 0)
        self.user.save(update_fields=["day_start_time"])

        self.assertEqual(
            logical_date_for(self.user, at(LONDON, 2026, 3, 4, 5, 0)),
            date(2026, 3, 3),
        )
        self.assertEqual(
            logical_date_for(self.user, at(LONDON, 2026, 3, 4, 7, 0)),
            date(2026, 3, 4),
        )

    def test_accepts_a_player_as_well_as_a_user(self):
        moment = at(LONDON, 2026, 3, 4, 1, 0)

        self.assertEqual(
            logical_date_for(self.player, moment),
            logical_date_for(self.user, moment),
        )

    def test_rejects_a_naive_datetime(self):
        with self.assertRaises(ValueError):
            logical_date_for(self.user, datetime(2026, 3, 4, 1, 0))

    def test_falls_back_to_defaults_for_an_unusable_timezone(self):
        """
        TimeZoneField validates on assignment, so a bad value can only
        arrive from outside the ORM - but day_settings still has to cope,
        since it runs on every day computation.
        """
        broken = SimpleNamespace(timezone="Not/AZone", day_start_time=None)

        tz, day_start = day_settings(broken)

        self.assertEqual(str(tz), "UTC")
        self.assertEqual(day_start, DEFAULT_DAY_START)


class AmbientTimezoneIndependenceTests(TestCase):
    """
    The day must not depend on whatever timezone happens to be activated.

    `UserTimezoneMiddleware` only activates the user's timezone during HTTP
    requests, so before this the same player got a different day boundary
    depending on whether they pressed Submit (request context, their
    timezone) or the server closed the session for them (Celery/consumer
    context, UTC).
    """

    def test_same_answer_whatever_timezone_is_activated(self):
        user = user_factory(with_player=True, timezone="America/New_York")
        moment = at(ZoneInfo("UTC"), 2026, 3, 4, 3, 0)

        timezone.activate(ZoneInfo("Australia/Sydney"))
        try:
            with_ambient = logical_date_for(user, moment)
        finally:
            timezone.deactivate()

        without_ambient = logical_date_for(user, moment)

        self.assertEqual(with_ambient, without_ambient)
        self.assertEqual(with_ambient, date(2026, 3, 3))


class LogicalDayBoundsTests(TestCase):
    def setUp(self):
        self.user = user_factory(with_player=True, timezone="Europe/London")

    def test_bounds_span_the_cutoff_to_the_next_cutoff(self):
        start, end = logical_day_bounds(self.user, date(2026, 3, 3))

        self.assertEqual(start, at(LONDON, 2026, 3, 3, 2, 0))
        self.assertEqual(end, at(LONDON, 2026, 3, 4, 2, 0))

    def test_bounds_are_half_open_and_agree_with_logical_date_for(self):
        day = date(2026, 3, 3)
        start, end = logical_day_bounds(self.user, day)

        self.assertEqual(logical_date_for(self.user, start), day)
        self.assertEqual(logical_date_for(self.user, end - timedelta(seconds=1)), day)
        # The end instant belongs to the next day, not this one.
        self.assertEqual(logical_date_for(self.user, end), day + timedelta(days=1))

    def test_a_dst_day_is_still_bounded_by_local_wall_clock_times(self):
        """
        The UK springs forward at 01:00 UTC on 2026-03-29, so the logical
        day starting 2026-03-28 contains the transition and is only 23 hours
        long. It must still begin and end at 02:00 local - shifting a UTC
        instant by 24h instead would drift the boundary by an hour.
        """
        start, end = logical_day_bounds(self.user, date(2026, 3, 28))

        self.assertEqual(start.astimezone(LONDON).hour, 2)
        self.assertEqual(end.astimezone(LONDON).hour, 2)
        self.assertEqual(start.utcoffset(), timedelta(0))
        self.assertEqual(end.utcoffset(), timedelta(hours=1))
        # Compared in UTC deliberately: subtracting two aware datetimes that
        # share a tzinfo instance is done on wall-clock values and ignores
        # the offset change, so `end - start` alone would read as 24 hours.
        self.assertEqual(
            end.astimezone(UTC) - start.astimezone(UTC), timedelta(hours=23)
        )


class LogicalDateStampingTests(TestCase):
    """`logical_date` is stamped once, when the session starts."""

    def setUp(self):
        self.user = user_factory(with_player=True, timezone="Europe/London")
        self.player = self.user.player
        self.timer = self.player.activity_timer

    def test_starting_a_timer_stamps_the_activitys_logical_date(self):
        self.timer.new_activity(name="Write tests")
        self.timer.start()

        activity = self.timer.activity
        activity.refresh_from_db()

        self.assertIsNotNone(activity.logical_date)
        self.assertEqual(
            activity.logical_date,
            logical_date_for(self.player, activity.started_at),
        )

    def test_pause_and_resume_do_not_move_the_logical_date(self):
        self.timer.new_activity(name="Long session")
        self.timer.start()
        stamped = self.timer.activity.logical_date

        self.timer.pause()
        self.timer.start()
        self.timer.pause()
        self.timer.start()

        self.timer.activity.refresh_from_db()
        self.assertEqual(self.timer.activity.logical_date, stamped)

    def test_completing_does_not_move_the_logical_date(self):
        self.timer.new_activity(name="Finished session")
        self.timer.start()
        stamped = self.timer.activity.logical_date
        activity_id = self.timer.activity.pk

        self.timer.complete()

        self.assertEqual(
            PlayerActivity.objects.get(pk=activity_id).logical_date, stamped
        )

    def test_an_activity_saved_without_a_logical_date_gets_one(self):
        """
        The backstop for every path that doesn't go through the timer -
        without it, a directly-created activity is invisible to daily goals.
        """
        activity = PlayerActivity.objects.create(
            player=self.player,
            name="Logged straight in",
            is_complete=True,
            duration=600,
            completed_at=timezone.now(),
        )

        self.assertEqual(
            activity.logical_date,
            logical_date_for(self.player, activity.completed_at),
        )


class LoginLogicalDateTests(TestCase):
    def setUp(self):
        self.user = user_factory(with_player=True, timezone="Europe/London")

    def test_a_login_stamps_its_logical_date_on_creation(self):
        login = UserLogin.objects.create(user=self.user)

        self.assertIsNotNone(login.logical_date)
        self.assertEqual(login.logical_date, current_logical_date(self.user))

    def test_a_small_hours_login_belongs_to_the_previous_day(self):
        login = UserLogin.objects.create(user=self.user)
        moment = at(LONDON, 2026, 3, 4, 1, 0)
        UserLogin.objects.filter(pk=login.pk).update(
            timestamp=moment, logical_date=logical_date_for(self.user, moment)
        )
        login.refresh_from_db()

        self.assertEqual(login.local_date(), date(2026, 3, 3))

    def test_local_date_falls_back_for_rows_predating_the_column(self):
        login = UserLogin.objects.create(user=self.user)
        UserLogin.objects.filter(pk=login.pk).update(logical_date=None)
        login.refresh_from_db()

        self.assertEqual(
            login.local_date(), logical_date_for(self.user, login.timestamp)
        )


class DailyGoalsLogicalDayTests(TestCase):
    """
    Goals follow the session's own day, so late-evening work counts for the
    day it was worked rather than the one the clock rolled into.
    """

    def setUp(self):
        self.user = user_factory(with_player=True, timezone="Europe/London")
        self.player = self.user.player

    def _activity_at(self, started, minutes=10):
        activity = PlayerActivity.objects.create(
            player=self.player,
            name="Evening work",
            is_complete=True,
            duration=minutes * 60,
            started_at=started,
            completed_at=started + timedelta(minutes=minutes),
        )
        return activity

    def test_a_late_session_counts_for_the_day_it_started(self):
        from progression.daily_goals import get_daily_goals_state

        tuesday_night = at(LONDON, 2026, 3, 3, 23, 30)
        self._activity_at(tuesday_night)

        tuesday = get_daily_goals_state(self.player, today=date(2026, 3, 3))
        wednesday = get_daily_goals_state(self.player, today=date(2026, 3, 4))

        self.assertTrue(tuesday.completed_activity_today)
        self.assertEqual(tuesday.activity_minutes_today, 10)
        # ...and does not also credit the following day.
        self.assertFalse(wednesday.completed_activity_today)

    def test_a_session_crossing_midnight_is_not_split(self):
        from progression.daily_goals import get_daily_goals_state

        self._activity_at(at(LONDON, 2026, 3, 3, 23, 30), minutes=60)

        tuesday = get_daily_goals_state(self.player, today=date(2026, 3, 3))
        wednesday = get_daily_goals_state(self.player, today=date(2026, 3, 4))

        self.assertEqual(tuesday.activity_minutes_today, 60)
        self.assertEqual(wednesday.activity_minutes_today, 0)
