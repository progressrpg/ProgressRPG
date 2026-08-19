"""
Tests for the stale-connection auto-complete sweep.

If a websocket connection dies without a clean disconnect (crash, sleep,
dropped network), TimerConsumer.disconnect() never fires, so its
grace-period auto-complete never runs. auto_complete_timers_for_stale_players
is a periodic backstop: it completes any active ActivityTimer whose player's
last_seen heartbeat has gone stale.
"""

from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from gameplay.models import ActivityTimer
from gameplay.tasks import (
    STALE_TIMER_THRESHOLD,
    auto_complete_timers_for_stale_players,
    truncate_to_last_heartbeat,
)
from users.tests import user_factory


class AutoCompleteStaleTimersTaskTests(TestCase):
    def setUp(self):
        self.user = user_factory(with_player=True)
        self.player = self.user.player
        self.timer = self.player.activity_timer

    def _make_active(self, last_seen):
        self.timer.status = "active"
        self.timer.start_time = timezone.now()
        self.timer.save(update_fields=["status", "start_time"])
        self.player.last_seen = last_seen
        self.player.save(update_fields=["last_seen"])

    # fresh heartbeat — untouched

    def test_does_not_complete_timer_with_fresh_heartbeat(self):
        self._make_active(timezone.now())

        with patch.object(ActivityTimer, "complete") as mock_complete:
            result = auto_complete_timers_for_stale_players()

        mock_complete.assert_not_called()
        self.assertEqual(result, 0)

    def test_does_not_complete_timer_just_under_threshold(self):
        self._make_active(
            timezone.now() - (STALE_TIMER_THRESHOLD - timedelta(seconds=1))
        )

        with patch.object(ActivityTimer, "complete") as mock_complete:
            auto_complete_timers_for_stale_players()

        mock_complete.assert_not_called()

    # stale heartbeat — completed

    def test_completes_timer_when_last_seen_older_than_threshold(self):
        self._make_active(
            timezone.now() - (STALE_TIMER_THRESHOLD + timedelta(seconds=1))
        )

        with patch.object(ActivityTimer, "complete") as mock_complete, patch(
            "gameplay.tasks.broadcast_activity_timer"
        ) as mock_broadcast:
            result = auto_complete_timers_for_stale_players()

        mock_complete.assert_called_once_with(completion_source="auto")
        self.assertEqual(result, 1)
        # Any other open session (tabs/devices) for this player should be
        # told the timer was auto-completed by this sweep.
        mock_broadcast.assert_called_once_with(self.timer)

    def test_completes_timer_when_last_seen_was_never_set(self):
        self._make_active(None)

        with patch.object(ActivityTimer, "complete") as mock_complete:
            result = auto_complete_timers_for_stale_players()

        mock_complete.assert_called_once_with(completion_source="auto")
        self.assertEqual(result, 1)

    # non-active timers — ignored regardless of staleness

    def test_ignores_paused_timer_with_stale_heartbeat(self):
        self._make_active(
            timezone.now() - (STALE_TIMER_THRESHOLD + timedelta(seconds=1))
        )
        self.timer.status = "paused"
        self.timer.save(update_fields=["status"])

        with patch.object(ActivityTimer, "complete") as mock_complete:
            result = auto_complete_timers_for_stale_players()

        mock_complete.assert_not_called()
        self.assertEqual(result, 0)

    def test_ignores_empty_timer_with_stale_heartbeat(self):
        self.player.last_seen = timezone.now() - (
            STALE_TIMER_THRESHOLD + timedelta(seconds=1)
        )
        self.player.save(update_fields=["last_seen"])
        # Default timer status after player creation is "empty"

        with patch.object(ActivityTimer, "complete") as mock_complete:
            result = auto_complete_timers_for_stale_players()

        mock_complete.assert_not_called()
        self.assertEqual(result, 0)

    def test_ignores_completed_timer_with_stale_heartbeat(self):
        self._make_active(
            timezone.now() - (STALE_TIMER_THRESHOLD + timedelta(seconds=1))
        )
        self.timer.status = "completed"
        self.timer.save(update_fields=["status"])

        with patch.object(ActivityTimer, "complete") as mock_complete:
            result = auto_complete_timers_for_stale_players()

        mock_complete.assert_not_called()
        self.assertEqual(result, 0)

    # multiple players

    def test_completes_multiple_stale_timers_and_skips_fresh_ones(self):
        stale_last_seen = timezone.now() - (
            STALE_TIMER_THRESHOLD + timedelta(seconds=1)
        )

        other_user = user_factory(with_player=True)
        other_player = other_user.player
        other_timer = other_player.activity_timer
        other_timer.status = "active"
        other_timer.start_time = timezone.now()
        other_timer.save(update_fields=["status", "start_time"])
        other_player.last_seen = stale_last_seen
        other_player.save(update_fields=["last_seen"])

        self._make_active(timezone.now())  # fresh — should be left alone

        with patch.object(ActivityTimer, "complete") as mock_complete:
            result = auto_complete_timers_for_stale_players()

        mock_complete.assert_called_once_with(completion_source="auto")
        self.assertEqual(result, 1)


class RegisterConnectionLastSeenTests(TestCase):
    def setUp(self):
        self.user = user_factory(with_player=True)
        self.player = self.user.player

    def test_register_connection_stamps_last_seen(self):
        self.assertIsNone(self.player.last_seen)

        self.player.register_connection()

        self.assertIsNotNone(self.player.last_seen)


class StaleTimerThresholdTests(TestCase):
    """
    The threshold has to absorb a browser throttling or suspending the tab's
    heartbeat interval, not just one late ping. It previously sat at 90s —
    a single missed ping — and was auto-completing the timers of players who
    had simply switched to another window to do the thing they were timing.
    """

    # Mirrors HEARTBEAT_INTERVAL_MS in frontend/src/hooks/useWebSocketHeartbeat.ts.
    HEARTBEAT_INTERVAL = timedelta(seconds=25)

    def test_threshold_tolerates_many_consecutive_missed_heartbeats(self):
        self.assertGreaterEqual(STALE_TIMER_THRESHOLD, self.HEARTBEAT_INTERVAL * 10)

    def test_backgrounded_tab_with_a_throttled_heartbeat_is_not_swept(self):
        user = user_factory(with_player=True)
        player = user.player
        timer = player.activity_timer
        timer.status = "active"
        timer.start_time = timezone.now()
        timer.save(update_fields=["status", "start_time"])

        # Chrome clamps a hidden tab to roughly one wake-up a minute; five
        # minutes of that is a player working in another window, not a dead
        # connection.
        player.last_seen = timezone.now() - timedelta(minutes=5)
        player.save(update_fields=["last_seen"])

        with patch.object(ActivityTimer, "complete") as mock_complete:
            result = auto_complete_timers_for_stale_players()

        mock_complete.assert_not_called()
        self.assertEqual(result, 0)


class TruncateToLastHeartbeatTests(TestCase):
    """
    Auto-completes credit time up to the last confirmed heartbeat rather than
    up to now, so the window we wait before giving up on a player can be
    generous without inflating the XP awarded when we do.
    """

    def setUp(self):
        self.user = user_factory(with_player=True)
        self.player = self.user.player
        self.timer = self.player.activity_timer

    def _make_active(self, start_time, last_seen, elapsed_time=0):
        self.timer.status = "active"
        self.timer.start_time = start_time
        self.timer.elapsed_time = elapsed_time
        self.timer.save(update_fields=["status", "start_time", "elapsed_time"])
        self.player.last_seen = last_seen
        self.player.save(update_fields=["last_seen"])
        self.timer.refresh_from_db()

    def test_banks_only_the_time_up_to_the_last_heartbeat(self):
        now = timezone.now()
        self._make_active(
            start_time=now - timedelta(minutes=20),
            last_seen=now - timedelta(minutes=12),
        )

        truncate_to_last_heartbeat(self.timer)

        self.timer.refresh_from_db()
        self.assertAlmostEqual(self.timer.elapsed_time, 8 * 60, delta=2)
        self.assertIsNone(self.timer.start_time)

    def test_adds_to_time_already_banked_by_an_earlier_pause(self):
        now = timezone.now()
        self._make_active(
            start_time=now - timedelta(minutes=10),
            last_seen=now - timedelta(minutes=4),
            elapsed_time=300,
        )

        truncate_to_last_heartbeat(self.timer)

        self.timer.refresh_from_db()
        self.assertAlmostEqual(self.timer.elapsed_time, 300 + 6 * 60, delta=2)

    def test_no_op_when_the_heartbeat_predates_the_current_run(self):
        now = timezone.now()
        self._make_active(
            start_time=now - timedelta(minutes=5),
            last_seen=now - timedelta(minutes=30),
            elapsed_time=120,
        )

        truncate_to_last_heartbeat(self.timer)

        self.timer.refresh_from_db()
        self.assertEqual(self.timer.elapsed_time, 120)
        self.assertIsNotNone(self.timer.start_time)

    def test_no_op_when_the_player_never_sent_a_heartbeat(self):
        self._make_active(
            start_time=timezone.now() - timedelta(minutes=5),
            last_seen=None,
        )

        truncate_to_last_heartbeat(self.timer)

        self.timer.refresh_from_db()
        self.assertEqual(self.timer.elapsed_time, 0)

    def test_sweep_does_not_award_xp_for_the_wait_before_giving_up(self):
        now = timezone.now()
        self._make_active(
            start_time=now - timedelta(minutes=25),
            last_seen=now - (STALE_TIMER_THRESHOLD + timedelta(minutes=5)),
        )

        with patch("gameplay.tasks.broadcast_activity_timer"):
            auto_complete_timers_for_stale_players()

        self.timer.refresh_from_db()
        expected = 25 * 60 - int(
            (STALE_TIMER_THRESHOLD + timedelta(minutes=5)).total_seconds()
        )
        self.assertAlmostEqual(self.timer.elapsed_time, expected, delta=2)
