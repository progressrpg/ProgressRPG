"""
Tests for the disconnect grace period.

On disconnect with an active timer the consumer schedules
auto_complete_timer_on_disconnect via Celery and stores the task ID in
Redis.  On reconnect the consumer revokes that task.  If the player
never comes back the task calls ActivityTimer.complete(), awarding XP.
"""

from datetime import timedelta

from asgiref.sync import async_to_sync
from unittest.mock import AsyncMock, MagicMock, patch

from django.core.cache import cache
from django.test import TransactionTestCase
from django.utils import timezone

from gameplay.consumers import (
    DISCONNECT_GRACE_SECONDS,
    DISCONNECT_TASK_CACHE_KEY,
    TimerConsumer,
)
from gameplay.models import ActivityTimer
from gameplay.tasks import auto_complete_timer_on_disconnect

from users.tests import user_factory

# ── shared test infrastructure ─────────────────────────────────────────────────


def _run_task(player_id, task_id):
    """
    Run the task synchronously (via apply()) with a known task ID so the
    supersede guard inside the task sees the right self.request.id.
    """
    return auto_complete_timer_on_disconnect.apply(
        kwargs={"player_id": player_id},
        task_id=task_id,
    ).get()


class DummyChannelLayer:
    def __init__(self):
        self.groups = set()
        self.group_messages = []

    async def group_add(self, group, channel_name):
        self.groups.add(group)

    async def group_discard(self, group, channel_name):
        self.groups.discard(group)

    async def group_send(self, group, message):
        self.group_messages.append((group, message))


class AsyncCallRecorder:
    def __init__(self, return_value=None):
        self.calls = []
        self.return_value = return_value

    async def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.return_value


class MockTimer:
    def __init__(self, status="empty"):
        self.status = status


# ── Celery task tests ──────────────────────────────────────────────────────────


class AutoCompleteTimerTaskTests(TransactionTestCase):
    TASK_ID = "test-task-abc123"

    def setUp(self):
        self.user = user_factory(with_player=True)
        self.player = self.user.player
        self.timer = self.player.activity_timer
        cache.clear()

    def tearDown(self):
        cache.clear()

    def _cache_key(self):
        return DISCONNECT_TASK_CACHE_KEY.format(player_id=self.player.id)

    def _prime_cache(self, task_id=None):
        cache.set(self._cache_key(), task_id or self.TASK_ID)

    # supersede guard

    def test_superseded_task_returns_superseded_and_does_not_touch_timer(self):
        cache.set(self._cache_key(), "different-task-id")

        with patch.object(ActivityTimer, "complete") as mock_complete:
            result = _run_task(self.player.id, self.TASK_ID)

        self.assertEqual(result, "superseded")
        mock_complete.assert_not_called()

    # missing timer

    def test_returns_no_timer_when_player_has_no_activity_timer(self):
        self.timer.delete()
        self._prime_cache()

        result = _run_task(self.player.id, self.TASK_ID)

        self.assertEqual(result, "no_timer")

    # timer not active — skipped cases

    def test_returns_skipped_and_clears_cache_when_timer_is_empty(self):
        # Default status after player creation is "empty"
        self._prime_cache()

        result = _run_task(self.player.id, self.TASK_ID)

        self.assertEqual(result, "skipped:empty")
        self.assertIsNone(cache.get(self._cache_key()))

    def test_returns_skipped_for_paused_and_completed_timers(self):
        for status in ["paused", "completed"]:
            self.timer.status = status
            self.timer.save(update_fields=["status"])
            self._prime_cache()

            result = _run_task(self.player.id, self.TASK_ID)

            self.assertEqual(result, f"skipped:{status}")

    # active timer — completion path

    def test_does_not_complete_when_player_still_has_a_live_connection(self):
        """
        A player with two tabs open who closes one, or whose reconnect raced
        ahead of the old socket's disconnect, still has an active connection
        and a running timer — nothing runs connect() again to revoke this
        task, so the task itself has to stand down.
        """
        self.timer.status = "active"
        self.timer.start_time = timezone.now()
        self.timer.save(update_fields=["status", "start_time"])
        self.player.active_connections = 1
        self.player.save(update_fields=["active_connections"])
        self._prime_cache()

        with patch.object(ActivityTimer, "complete") as mock_complete, patch(
            "gameplay.tasks.broadcast_activity_timer"
        ) as mock_broadcast:
            result = _run_task(self.player.id, self.TASK_ID)

        self.assertEqual(result, "still_connected")
        mock_complete.assert_not_called()
        mock_broadcast.assert_not_called()
        self.assertIsNone(cache.get(self._cache_key()))

    def test_credits_only_time_up_to_the_last_heartbeat(self):
        now = timezone.now()
        self.timer.status = "active"
        self.timer.start_time = now - timedelta(minutes=10)
        self.timer.save(update_fields=["status", "start_time"])
        self.player.active_connections = 0
        self.player.last_seen = now - timedelta(minutes=2)
        self.player.save(update_fields=["active_connections", "last_seen"])
        self._prime_cache()

        with patch("gameplay.tasks.broadcast_activity_timer"):
            result = _run_task(self.player.id, self.TASK_ID)

        self.assertEqual(result, "completed")
        self.timer.refresh_from_db()
        self.assertAlmostEqual(self.timer.elapsed_time, 8 * 60, delta=2)

    def test_completes_active_timer_and_clears_cache(self):
        self.timer.status = "active"
        self.timer.start_time = timezone.now()
        self.timer.save(update_fields=["status", "start_time"])
        self._prime_cache()

        with patch.object(
            ActivityTimer, "complete", return_value={"xp_gained": 50}
        ) as mock_complete, patch(
            "gameplay.tasks.broadcast_activity_timer"
        ) as mock_broadcast:
            result = _run_task(self.player.id, self.TASK_ID)

        self.assertEqual(result, "completed")
        mock_complete.assert_called_once_with(completion_source="auto")
        self.assertIsNone(cache.get(self._cache_key()))
        # Any other open session (tabs/devices) for this player should be
        # told the timer was auto-completed, so it stops ticking a timer
        # the server has already closed out.
        mock_broadcast.assert_called_once_with(self.timer)


# ── consumer disconnect tests ──────────────────────────────────────────────────


class TimerConsumerDisconnectGraceTests(TransactionTestCase):

    def setUp(self):
        self.user = user_factory(with_player=True)
        self.player = self.user.player
        cache.clear()

    def tearDown(self):
        cache.clear()

    def _cache_key(self):
        return DISCONNECT_TASK_CACHE_KEY.format(player_id=self.player.id)

    def _make_consumer(self, timer_status="active"):
        consumer = TimerConsumer()
        consumer.scope = {"user": self.user}
        consumer.channel_layer = DummyChannelLayer()
        consumer.channel_name = "test.channel.grace"
        consumer.player = self.player
        consumer.player_group = f"player_{self.player.id}"
        consumer.character = None
        consumer.link = None
        consumer.activity_timer = MockTimer(status=timer_status)
        return consumer

    def _disconnect_with_mock_task(self, consumer):
        """Run disconnect() with apply_async stubbed out; return the mock task."""
        mock_result = MagicMock()
        mock_result.id = "scheduled-task-id"

        with patch("gameplay.tasks.auto_complete_timer_on_disconnect") as mock_task:
            mock_task.apply_async.return_value = mock_result
            async_to_sync(consumer.disconnect)(1000)

        return mock_task

    # active timer → task scheduled

    def test_active_timer_schedules_task_stores_cache_and_skips_pause(self):
        consumer = self._make_consumer(timer_status="active")
        mock_result = MagicMock()
        mock_result.id = "scheduled-task-id"

        with patch("gameplay.tasks.auto_complete_timer_on_disconnect") as mock_task:
            mock_task.apply_async.return_value = mock_result
            with patch(
                "gameplay.consumers.control_timers", new_callable=AsyncMock
            ) as mock_control:
                async_to_sync(consumer.disconnect)(1000)

        mock_task.apply_async.assert_called_once_with(
            kwargs={"player_id": self.player.id},
            countdown=DISCONNECT_GRACE_SECONDS,
        )
        self.assertEqual(cache.get(self._cache_key()), "scheduled-task-id")
        mock_control.assert_not_called()

    # non-active timers → no task scheduled

    def test_does_not_schedule_task_for_empty_paused_or_completed_timers(self):
        for status in ["empty", "paused", "completed"]:
            consumer = self._make_consumer(timer_status=status)

            mock_task = self._disconnect_with_mock_task(consumer)

            mock_task.apply_async.assert_not_called()
            self.assertIsNone(cache.get(self._cache_key()))

    # waiting timer → immediate pause (preserved existing behaviour)

    def test_pauses_immediately_when_timer_is_waiting(self):
        consumer = self._make_consumer(timer_status="waiting")

        with patch("gameplay.tasks.auto_complete_timer_on_disconnect") as mock_task:
            mock_task.apply_async.return_value = MagicMock(id="x")
            with patch(
                "gameplay.consumers.control_timers", new_callable=AsyncMock
            ) as mock_control:
                async_to_sync(consumer.disconnect)(1000)

        mock_task.apply_async.assert_not_called()
        mock_control.assert_called_once_with(
            consumer.player, consumer.activity_timer, "pause"
        )


# ── consumer reconnect tests ───────────────────────────────────────────────────


class TimerConsumerReconnectTests(TransactionTestCase):

    def setUp(self):
        self.user = user_factory(with_player=True)
        self.player = self.user.player
        cache.clear()

    def tearDown(self):
        cache.clear()

    def _cache_key(self):
        return DISCONNECT_TASK_CACHE_KEY.format(player_id=self.player.id)

    def _make_consumer(self):
        consumer = TimerConsumer()
        consumer.scope = {"user": self.user}
        consumer.channel_layer = DummyChannelLayer()
        consumer.channel_name = "test.channel.reconnect"
        consumer.accept = AsyncCallRecorder()
        consumer.close = AsyncCallRecorder()
        consumer.send_json = AsyncCallRecorder()
        consumer._send_pending_messages = AsyncCallRecorder()
        consumer.get_activity_timer = AsyncCallRecorder(return_value=None)
        return consumer

    def test_reconnect_revokes_pending_task_and_clears_cache(self):
        cache.set(self._cache_key(), "pending-task-id")
        consumer = self._make_consumer()

        with patch("gameplay.consumers.current_app") as mock_celery:
            async_to_sync(consumer.connect)()

        mock_celery.control.revoke.assert_called_once_with("pending-task-id")
        self.assertIsNone(cache.get(self._cache_key()))

    def test_does_not_revoke_when_no_pending_task(self):
        consumer = self._make_consumer()

        with patch("gameplay.consumers.current_app") as mock_celery:
            async_to_sync(consumer.connect)()

        mock_celery.control.revoke.assert_not_called()
