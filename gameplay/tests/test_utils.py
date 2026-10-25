"""
Tests for gameplay.utils - the server-side timer control helpers and the
websocket fan-out they drive.

These functions sit on the PlayerCharacterLink websocket path, which is
currently mid-re-enablement: TimerConsumer.set_player_and_character() returns
a null character/link, so handle_client_request's create_activity/
submit_activity branches (and therefore start_activity_and_broadcast/
complete_activity_and_broadcast) are not reachable from a live socket yet.
They are tested here regardless, because that is exactly the code about to
become reachable.
"""

from unittest.mock import patch

from asgiref.sync import async_to_sync
from django.test import TestCase, TransactionTestCase

from character.models import Character
from gameplay.utils import (
    complete_activity_and_broadcast,
    control_timers,
    pause_server_timers,
    start_activity_and_broadcast,
    start_server_timers,
)
from users.tests import user_factory


class RecordingAsyncSend:
    """Stand-in for gameplay.utils.send_group_message that records its calls."""

    def __init__(self):
        self.calls = []

    async def __call__(self, group_name, message):
        self.calls.append((group_name, message))
        return True

    @property
    def messages(self):
        return [message for _group, message in self.calls]


def _player_with_timer():
    return user_factory(with_player=True).player


class StartServerTimersTests(TestCase):
    def setUp(self):
        self.player = _player_with_timer()
        self.timer = self.player.activity_timer

    def test_starts_a_waiting_timer(self):
        self.timer.new_activity(name="Writing")
        self.assertEqual(self.timer.status, "waiting")

        success, _message = start_server_timers(self.timer)

        self.assertTrue(success)
        self.assertEqual(self.timer.status, "active")

    def test_refuses_an_empty_timer(self):
        self.assertEqual(self.timer.status, "empty")

        success, message = start_server_timers(self.timer)

        self.assertFalse(success)
        self.assertIn("not in a valid state", message)
        self.assertEqual(self.timer.status, "empty")

    def test_activates_the_activity_xp_modifiers(self):
        self.timer.new_activity(name="Writing")

        with patch(
            "gameplay.services.xp_modifiers.set_activity_active_modifiers"
        ) as mock_set:
            start_server_timers(self.timer)

        mock_set.assert_called_once_with(self.player, is_active=True)

    def test_reports_failure_instead_of_raising_when_start_errors(self):
        self.timer.new_activity(name="Writing")

        with patch.object(
            type(self.timer), "start", side_effect=RuntimeError("boom")
        ):
            success, message = start_server_timers(self.timer)

        self.assertFalse(success)
        self.assertIn("boom", message)


class PauseServerTimersTests(TestCase):
    def setUp(self):
        self.player = _player_with_timer()
        self.timer = self.player.activity_timer

    def test_pauses_an_active_timer(self):
        self.timer.new_activity(name="Writing", start_immediately=True)
        self.assertEqual(self.timer.status, "active")

        success, _message = pause_server_timers(self.timer)

        self.assertTrue(success)
        self.assertEqual(self.timer.status, "paused")

    def test_leaves_an_empty_timer_alone(self):
        self.assertEqual(self.timer.status, "empty")

        success, _message = pause_server_timers(self.timer)

        # Reports success without touching the timer: there is nothing to
        # pause, which is not an error.
        self.assertTrue(success)
        self.assertEqual(self.timer.status, "empty")

    def test_deactivates_the_activity_xp_modifiers(self):
        self.timer.new_activity(name="Writing", start_immediately=True)

        with patch(
            "gameplay.services.xp_modifiers.set_activity_active_modifiers"
        ) as mock_set:
            pause_server_timers(self.timer)

        mock_set.assert_called_once_with(self.player, is_active=False)


class ControlTimersTests(TransactionTestCase):
    """
    TransactionTestCase because control_timers is async and reaches the DB
    through database_sync_to_async, which runs in a thread that cannot see a
    TestCase's wrapping transaction. Matches test_consumers.py.
    """

    def setUp(self):
        self.player = _player_with_timer()
        self.timer = self.player.activity_timer
        self.send = RecordingAsyncSend()

    def _control(self, mode):
        with patch("gameplay.utils.send_group_message", self.send):
            return async_to_sync(control_timers)(self.player, self.timer, mode)

    def test_start_mode_starts_the_timer_and_broadcasts(self):
        self.timer.new_activity(name="Writing")

        result = self._control("start")

        self.assertTrue(result)
        self.timer.refresh_from_db()
        self.assertEqual(self.timer.status, "active")

        group, message = self.send.calls[0]
        self.assertEqual(group, f"player_{self.player.id}")
        self.assertEqual(
            message, {"type": "action", "action": "start_timers", "success": True}
        )

    def test_pause_mode_pauses_the_timer_and_broadcasts(self):
        self.timer.new_activity(name="Writing", start_immediately=True)

        result = self._control("pause")

        self.assertTrue(result)
        self.timer.refresh_from_db()
        self.assertEqual(self.timer.status, "paused")

        _group, message = self.send.calls[0]
        self.assertEqual(
            message, {"type": "action", "action": "pause_timers", "success": True}
        )

    def test_failed_start_broadcasts_the_reason_and_returns_false(self):
        # Empty timer: start_server_timers refuses it.
        result = self._control("start")

        self.assertFalse(result)
        _group, message = self.send.calls[0]
        self.assertEqual(message["type"], "response")
        self.assertEqual(message["action"], "console.log")
        self.assertIn("not in a valid state", message["message"])

    def test_invalid_mode_returns_false_and_broadcasts_the_reason(self):
        """
        Regression test. The `else` branch used to log "Invalid mode" and
        fall through to `if server_success:`, which read an unbound local
        and raised UnboundLocalError instead of reporting failure.
        """
        result = self._control("sideways")

        self.assertFalse(result)
        _group, message = self.send.calls[0]
        self.assertEqual(message["type"], "response")
        self.assertEqual(message["action"], "console.log")
        self.assertIn("Invalid mode", message["message"])

    def test_invalid_mode_leaves_the_timer_untouched(self):
        self.timer.new_activity(name="Writing")

        self._control("sideways")

        self.timer.refresh_from_db()
        self.assertEqual(self.timer.status, "waiting")


class StartActivityAndBroadcastTests(TestCase):
    def setUp(self):
        self.player = _player_with_timer()
        self.timer = self.player.activity_timer
        self.character = Character.objects.create(given_name="Hero")
        self.send = RecordingAsyncSend()

    def test_broadcasts_create_activity_on_success(self):
        self.timer.new_activity(name="Writing")

        with patch("gameplay.utils.send_group_message", self.send):
            result = start_activity_and_broadcast(self.player, self.character)

        self.assertTrue(result)
        _group, message = self.send.calls[0]
        self.assertEqual(
            message, {"type": "action", "action": "create_activity"}
        )

    def test_broadcasts_the_reason_on_failure(self):
        # Empty timer: start_server_timers refuses it.
        with patch("gameplay.utils.send_group_message", self.send):
            result = start_activity_and_broadcast(self.player, self.character)

        self.assertFalse(result)
        _group, message = self.send.calls[0]
        self.assertEqual(message["action"], "console.log")
        self.assertIn("not in a valid state", message["message"])


class CompleteActivityAndBroadcastTests(TestCase):
    def setUp(self):
        self.player = _player_with_timer()
        self.timer = self.player.activity_timer
        self.character = Character.objects.create(given_name="Hero")
        self.send = RecordingAsyncSend()

    def test_broadcasts_submit_activity_on_success(self):
        self.timer.new_activity(name="Writing", start_immediately=True)

        with patch("gameplay.utils.send_group_message", self.send):
            result = complete_activity_and_broadcast(self.player, self.character)

        self.assertTrue(result)
        _group, message = self.send.calls[0]
        self.assertEqual(
            message, {"type": "action", "action": "submit_activity"}
        )

    def test_broadcasts_a_warning_when_pausing_fails(self):
        self.timer.new_activity(name="Writing", start_immediately=True)

        with patch("gameplay.utils.send_group_message", self.send), patch(
            "gameplay.utils.pause_server_timers", return_value=(False, "nope")
        ):
            result = complete_activity_and_broadcast(self.player, self.character)

        self.assertFalse(result)
        _group, message = self.send.calls[0]
        self.assertEqual(message["type"], "error")
        self.assertEqual(message["message"], "Pausing timers failed")
