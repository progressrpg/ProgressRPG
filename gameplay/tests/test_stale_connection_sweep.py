"""
Tests for the stale-connection auto-complete sweep.

If a websocket connection dies without a clean disconnect (crash, sleep,
dropped network), TimerConsumer.disconnect() never fires, so its
grace-period auto-complete never runs. auto_pause_timers_for_stale_players
is a periodic backstop: it completes any active ActivityTimer whose player's
last_seen heartbeat has gone stale.
"""

from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from gameplay.consumers import HEARTBEAT_INTERVAL_SECONDS
from gameplay.models import ActivityTimer
from gameplay.tasks import (
    STALE_TIMER_THRESHOLD,
    auto_pause_timers_for_stale_players,
    truncate_to_last_heartbeat,
)
from users.tests import user_factory


class AutoPauseStaleTimersTaskTests(TestCase):
    def setUp(self):
        self.user = user_factory(with_player=True)
        self.player = self.user.player
        self.timer = self.player.activity_timer

    def _make_active(self, last_seen, timer=None, player=None):
        timer = timer or self.timer
        player = player or self.player
        # Through new_activity()/start(), because pausing a timer with no
        # activity attached resets it instead - no real session is ever in
        # that state, and a fixture that is would mask what pausing does.
        timer.new_activity(name="Stale session")
        timer.start()
        timer.start_time = timezone.now()
        timer.save(update_fields=["start_time"])
        player.last_seen = last_seen
        player.save(update_fields=["last_seen"])

    # fresh heartbeat — untouched

    def test_does_not_complete_timer_with_fresh_heartbeat(self):
        self._make_active(timezone.now())

        with patch.object(ActivityTimer, "complete") as mock_complete:
            result = auto_pause_timers_for_stale_players()

        mock_complete.assert_not_called()
        self.assertEqual(result, 0)

    def test_does_not_complete_timer_just_under_threshold(self):
        self._make_active(
            timezone.now() - (STALE_TIMER_THRESHOLD - timedelta(seconds=1))
        )

        with patch.object(ActivityTimer, "complete") as mock_complete:
            auto_pause_timers_for_stale_players()

        mock_complete.assert_not_called()

    # stale heartbeat — paused, never completed

    def test_pauses_timer_when_last_seen_older_than_threshold(self):
        self._make_active(
            timezone.now() - (STALE_TIMER_THRESHOLD + timedelta(seconds=1))
        )

        with patch.object(ActivityTimer, "complete") as mock_complete, patch(
            "gameplay.tasks.broadcast_activity_timer"
        ) as mock_broadcast:
            result = auto_pause_timers_for_stale_players()

        self.assertEqual(result, 1)
        # The server is guessing the player is gone. A wrong guess must cost
        # them a click, not force-submit the session they were in.
        mock_complete.assert_not_called()
        self.timer.refresh_from_db()
        self.assertEqual(self.timer.status, "paused")
        # Any other open session (tabs/devices) should be told, so it stops
        # ticking a timer the server has stopped.
        mock_broadcast.assert_called_once_with(self.timer)

    def test_pauses_timer_when_last_seen_was_never_set(self):
        self._make_active(None)

        with patch.object(ActivityTimer, "complete") as mock_complete:
            result = auto_pause_timers_for_stale_players()

        self.assertEqual(result, 1)
        mock_complete.assert_not_called()
        self.timer.refresh_from_db()
        self.assertEqual(self.timer.status, "paused")

    def test_pausing_banks_the_elapsed_time_for_the_player_to_resolve(self):
        now = timezone.now()
        last_seen = now - (STALE_TIMER_THRESHOLD + timedelta(seconds=1))
        self._make_active(last_seen)
        # Worked for ten minutes before the heartbeat went quiet.
        self.timer.start_time = last_seen - timedelta(minutes=10)
        self.timer.save(update_fields=["start_time"])

        with patch("gameplay.tasks.broadcast_activity_timer"):
            auto_pause_timers_for_stale_players()

        self.timer.refresh_from_db()
        self.assertAlmostEqual(self.timer.elapsed_time, 10 * 60, delta=2)
        self.assertTrue(self.timer.has_banked_time())

    # non-active timers — ignored regardless of staleness

    def test_ignores_paused_timer_with_stale_heartbeat(self):
        self._make_active(
            timezone.now() - (STALE_TIMER_THRESHOLD + timedelta(seconds=1))
        )
        self.timer.status = "paused"
        self.timer.save(update_fields=["status"])

        with patch.object(ActivityTimer, "complete") as mock_complete:
            result = auto_pause_timers_for_stale_players()

        mock_complete.assert_not_called()
        self.assertEqual(result, 0)

    def test_ignores_empty_timer_with_stale_heartbeat(self):
        self.player.last_seen = timezone.now() - (
            STALE_TIMER_THRESHOLD + timedelta(seconds=1)
        )
        self.player.save(update_fields=["last_seen"])
        # Default timer status after player creation is "empty"

        with patch.object(ActivityTimer, "complete") as mock_complete:
            result = auto_pause_timers_for_stale_players()

        mock_complete.assert_not_called()
        self.assertEqual(result, 0)

    def test_ignores_completed_timer_with_stale_heartbeat(self):
        self._make_active(
            timezone.now() - (STALE_TIMER_THRESHOLD + timedelta(seconds=1))
        )
        self.timer.status = "completed"
        self.timer.save(update_fields=["status"])

        with patch.object(ActivityTimer, "complete") as mock_complete:
            result = auto_pause_timers_for_stale_players()

        mock_complete.assert_not_called()
        self.assertEqual(result, 0)

    # multiple players

    def test_pauses_multiple_stale_timers_and_skips_fresh_ones(self):
        stale_last_seen = timezone.now() - (
            STALE_TIMER_THRESHOLD + timedelta(seconds=1)
        )

        other_user = user_factory(with_player=True)
        other_player = other_user.player
        other_timer = other_player.activity_timer
        self._make_active(stale_last_seen, timer=other_timer, player=other_player)

        self._make_active(timezone.now())  # fresh — should be left alone

        with patch("gameplay.tasks.broadcast_activity_timer"):
            result = auto_pause_timers_for_stale_players()

        self.assertEqual(result, 1)
        other_timer.refresh_from_db()
        self.timer.refresh_from_db()
        self.assertEqual(other_timer.status, "paused")
        self.assertEqual(self.timer.status, "active")


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
    `last_seen` is now stamped server-side, by TimerConsumer, for as long as
    it holds an open socket - so a lapse means the process holding that
    socket is gone, not that the player's browser throttled a timer.

    That is what lets the threshold be tight again. It sat at 90s when the
    signal came from a setInterval in the player's tab, which was a single
    missed ping of slack and interrupted the sessions of players who had
    simply switched to another window.
    """

    def test_threshold_tolerates_several_missed_server_stamps(self):
        """
        A missed stamp means the consumer's loop didn't run - a wedged or
        dying worker. A few in a row is the signal; one is noise.
        """
        interval = timedelta(seconds=HEARTBEAT_INTERVAL_SECONDS)

        self.assertGreaterEqual(STALE_TIMER_THRESHOLD, interval * 3)

    def test_a_session_whose_process_is_still_stamping_is_not_swept(self):
        user = user_factory(with_player=True)
        player = user.player
        timer = player.activity_timer
        timer.new_activity(name="Live session")
        timer.start()

        # One interval ago: the loop is running, the socket is held.
        player.last_seen = timezone.now() - timedelta(
            seconds=HEARTBEAT_INTERVAL_SECONDS
        )
        player.save(update_fields=["last_seen"])

        with patch("gameplay.tasks.broadcast_activity_timer"):
            result = auto_pause_timers_for_stale_players()

        timer.refresh_from_db()
        self.assertEqual(result, 0)
        self.assertEqual(timer.status, "active")

    def test_a_session_whose_process_died_mid_session_is_swept(self):
        user = user_factory(with_player=True)
        player = user.player
        timer = player.activity_timer
        timer.new_activity(name="Orphaned session")
        timer.start()

        # No stamps since well past the threshold: disconnect() never ran,
        # so nothing paused this timer and it would accrue forever.
        player.last_seen = timezone.now() - (
            STALE_TIMER_THRESHOLD + timedelta(minutes=1)
        )
        player.save(update_fields=["last_seen"])

        with patch("gameplay.tasks.broadcast_activity_timer"):
            result = auto_pause_timers_for_stale_players()

        timer.refresh_from_db()
        self.assertEqual(result, 1)
        self.assertEqual(timer.status, "paused")


class TruncateToLastHeartbeatTests(TestCase):
    """
    Auto-pauses bank time up to the last confirmed heartbeat rather than up
    to now, so the window we wait before giving up on a player can be
    generous without crediting the wait itself as time worked.
    """

    def setUp(self):
        self.user = user_factory(with_player=True)
        self.player = self.user.player
        self.timer = self.player.activity_timer

    def _make_active(self, start_time, last_seen, elapsed_time=0):
        # An activity has to be attached: pausing a timer without one resets
        # it rather than banking its time, and no real session lacks one.
        self.timer.new_activity(name="Interrupted session")
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

    def test_sweep_does_not_bank_the_wait_before_giving_up(self):
        now = timezone.now()
        self._make_active(
            start_time=now - timedelta(minutes=25),
            last_seen=now - (STALE_TIMER_THRESHOLD + timedelta(minutes=5)),
        )

        with patch("gameplay.tasks.broadcast_activity_timer"):
            auto_pause_timers_for_stale_players()

        self.timer.refresh_from_db()
        expected = 25 * 60 - int(
            (STALE_TIMER_THRESHOLD + timedelta(minutes=5)).total_seconds()
        )
        self.assertAlmostEqual(self.timer.elapsed_time, expected, delta=2)
