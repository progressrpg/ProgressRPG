"""
Tests for the stale-connection auto-complete sweep.

If a websocket connection dies without a clean disconnect (crash, sleep,
dropped network), TimerConsumer.disconnect() never fires, so its 30s
grace-period auto-complete never runs. auto_complete_timers_for_stale_players
is a periodic backstop: it completes any active ActivityTimer whose player's
last_seen heartbeat has gone stale.
"""

from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from gameplay.models import ActivityTimer
from gameplay.tasks import STALE_TIMER_THRESHOLD, auto_complete_timers_for_stale_players
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
