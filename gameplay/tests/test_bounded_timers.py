"""
Tests for bounded sessions - a timer with a declared duration.

The point of persisting the limit is that a bounded session has a knowable
end, so when the connection drops there is nothing to guess: it runs to that
end and completes there. That is what makes "keep my timer going while I'm
away from the device" safe, where an unbounded "never stop" setting would
let a closed laptop accrue indefinitely.
"""

from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from core.models import GameSettings
from gameplay.models import ActivityTimer
from progression.models import PlayerActivity
from gameplay.tasks import (
    auto_pause_timer_on_disconnect,
    auto_pause_timers_for_stale_players,
    complete_expired_bounded_timers,
)
from users.tests import user_factory


class SetLimitTests(TestCase):
    def setUp(self):
        self.user = user_factory(with_player=True)
        self.player = self.user.player
        self.timer = self.player.activity_timer

    def _free_ceiling(self):
        return int(GameSettings.current().free_timer_limit_seconds)

    def test_a_declared_duration_is_stored(self):
        with patch.object(type(self.player), "is_premium", True):
            self.timer.set_limit(45 * 60)

        self.timer.refresh_from_db()
        self.assertEqual(self.timer.limit_seconds, 45 * 60)
        self.assertTrue(self.timer.is_bounded())

    def test_no_duration_leaves_the_session_unbounded_for_premium(self):
        with patch.object(type(self.player), "is_premium", True):
            self.timer.set_limit(None)

        self.timer.refresh_from_db()
        self.assertIsNone(self.timer.limit_seconds)
        self.assertFalse(self.timer.is_bounded())

    def test_free_players_are_capped_even_with_no_duration_given(self):
        """
        The free-tier ceiling was previously enforced only in the browser,
        so it stopped applying the moment the tab was closed.
        """
        self.timer.set_limit(None)

        self.timer.refresh_from_db()
        self.assertEqual(self.timer.limit_seconds, self._free_ceiling())
        self.assertEqual(self.timer.limit_reason, "free_limit")

    def test_an_oversized_client_limit_is_clamped_server_side(self):
        self.timer.set_limit(self._free_ceiling() * 10)

        self.timer.refresh_from_db()
        self.assertEqual(self.timer.limit_seconds, self._free_ceiling())
        self.assertEqual(self.timer.limit_reason, "free_limit")

    def test_a_shorter_limit_than_the_ceiling_is_kept(self):
        chosen = self._free_ceiling() // 3
        self.timer.set_limit(chosen, reason="preset_limit")

        self.timer.refresh_from_db()
        self.assertEqual(self.timer.limit_seconds, chosen)
        self.assertEqual(self.timer.limit_reason, "preset_limit")

    def test_garbage_from_a_client_does_not_crash_or_bypass_the_cap(self):
        self.timer.set_limit("not a number")

        self.timer.refresh_from_db()
        self.assertEqual(self.timer.limit_seconds, self._free_ceiling())

    def test_a_new_activity_clears_the_previous_sessions_limit(self):
        with patch.object(type(self.player), "is_premium", True):
            self.timer.set_limit(45 * 60)
            self.timer.new_activity(name="Something else")

        self.timer.refresh_from_db()
        self.assertIsNone(self.timer.limit_seconds)


class LimitArithmeticTests(TestCase):
    def setUp(self):
        self.user = user_factory(with_player=True)
        self.player = self.user.player
        self.timer = self.player.activity_timer

    def _run_for(self, seconds, limit):
        self.timer.limit_seconds = limit
        self.timer.status = "active"
        self.timer.start_time = timezone.now() - timedelta(seconds=seconds)
        self.timer.elapsed_time = 0
        self.timer.save()

    def test_remaining_counts_down_toward_the_limit(self):
        self._run_for(600, limit=900)

        self.assertAlmostEqual(self.timer.limit_remaining(), 300, delta=2)
        self.assertFalse(self.timer.limit_reached())

    def test_the_limit_is_reached_once_the_duration_is_spent(self):
        self._run_for(901, limit=900)

        self.assertEqual(self.timer.limit_remaining(), 0)
        self.assertTrue(self.timer.limit_reached())

    def test_banked_time_from_an_earlier_segment_counts_toward_the_limit(self):
        """
        Otherwise pausing and resuming would be a way to run a bounded
        session indefinitely.
        """
        self.timer.limit_seconds = 900
        self.timer.status = "active"
        self.timer.elapsed_time = 800
        self.timer.start_time = timezone.now() - timedelta(seconds=150)
        self.timer.save()

        self.assertTrue(self.timer.limit_reached())

    def test_an_unbounded_session_has_no_remaining(self):
        self._run_for(600, limit=None)

        self.assertIsNone(self.timer.limit_remaining())
        self.assertFalse(self.timer.limit_reached())


class ExpiredBoundedSweepTests(TestCase):
    def setUp(self):
        self.user = user_factory(with_player=True)
        self.player = self.user.player
        self.timer = self.player.activity_timer

    def _bounded_session(self, ran_for, limit):
        # Goes through start() rather than setting status directly, so the
        # activity gets its logical_date stamped the way a real session does.
        self.timer.new_activity(name="Bounded session")
        self.timer.start()
        self.timer.limit_seconds = limit
        self.timer.elapsed_time = 0
        self.timer.start_time = timezone.now() - timedelta(seconds=ran_for)
        self.timer.save()

    def test_completes_a_session_that_has_run_out_its_duration(self):
        self._bounded_session(ran_for=1000, limit=900)
        activity_id = self.timer.activity_id

        with patch("gameplay.tasks.broadcast_activity_timer") as broadcast:
            result = complete_expired_bounded_timers()

        self.assertEqual(result, 1)
        self.assertTrue(PlayerActivity.objects.get(pk=activity_id).is_complete)
        broadcast.assert_called_once()

        # complete() resets the timer, so the player can start something new.
        self.timer.refresh_from_db()
        self.assertEqual(self.timer.status, "empty")
        self.assertIsNone(self.timer.limit_seconds)

    def test_credits_exactly_the_declared_duration_not_the_overrun(self):
        """Declared 15 minutes, ran 20 before the sweep noticed: 15 counts."""
        self._bounded_session(ran_for=1200, limit=900)
        activity_id = self.timer.activity_id

        with patch("gameplay.tasks.broadcast_activity_timer"):
            complete_expired_bounded_timers()

        self.assertEqual(PlayerActivity.objects.get(pk=activity_id).duration, 900)

    def test_the_session_keeps_the_day_it_started_on(self):
        self._bounded_session(ran_for=1000, limit=900)
        activity_id = self.timer.activity_id
        stamped = PlayerActivity.objects.get(pk=activity_id).logical_date

        with patch("gameplay.tasks.broadcast_activity_timer"):
            complete_expired_bounded_timers()

        self.assertEqual(
            PlayerActivity.objects.get(pk=activity_id).logical_date, stamped
        )

    def test_leaves_a_session_still_within_its_duration_alone(self):
        self._bounded_session(ran_for=300, limit=900)

        with patch("gameplay.tasks.broadcast_activity_timer"):
            result = complete_expired_bounded_timers()

        self.timer.refresh_from_db()
        self.assertEqual(result, 0)
        self.assertEqual(self.timer.status, "active")

    def test_ignores_unbounded_sessions_entirely(self):
        self._bounded_session(ran_for=100000, limit=None)

        with patch("gameplay.tasks.broadcast_activity_timer"):
            result = complete_expired_bounded_timers()

        self.timer.refresh_from_db()
        self.assertEqual(result, 0)
        self.assertEqual(self.timer.status, "active")


class BoundedSessionsSurviveAbsenceTests(TestCase):
    """
    The behaviour the whole phase exists for: a bounded session is not
    closed early just because the player's connection went away.
    """

    def setUp(self):
        self.user = user_factory(with_player=True)
        self.player = self.user.player
        self.timer = self.player.activity_timer
        self.timer.new_activity(name="Go for a run")
        self.timer.limit_seconds = 45 * 60
        self.timer.status = "active"
        self.timer.start_time = timezone.now() - timedelta(minutes=5)
        self.timer.save()

    def test_the_stale_sweep_skips_a_bounded_session(self):
        self.player.last_seen = timezone.now() - timedelta(hours=1)
        self.player.save(update_fields=["last_seen"])

        with patch.object(ActivityTimer, "complete") as complete:
            result = auto_pause_timers_for_stale_players()

        complete.assert_not_called()
        self.assertEqual(result, 0)

    def test_the_disconnect_task_stands_down_for_a_bounded_session(self):
        from django.core.cache import cache

        from gameplay.consumers import DISCONNECT_TASK_CACHE_KEY

        task_id = "bounded-task-id"
        cache.set(DISCONNECT_TASK_CACHE_KEY.format(player_id=self.player.id), task_id)

        with patch.object(ActivityTimer, "complete") as complete:
            result = auto_pause_timer_on_disconnect.apply(
                kwargs={"player_id": self.player.id}, task_id=task_id
            ).get()

        self.assertEqual(result, "bounded")
        complete.assert_not_called()
        cache.clear()
