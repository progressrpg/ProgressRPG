"""
Tests for the server-side `last_seen` heartbeat.

The loop runs for exactly as long as the consumer holds its socket, which
is what makes `last_seen` mean "an ASGI process is holding a socket for
this player" rather than "this player's tab is scheduling timers promptly".

Leaking the task is the failure to guard hardest against: a consumer that
doesn't cancel its loop keeps a departed player looking present forever, so
their timer is never swept. That is worse than the bug this replaces, and
silent - hence the "no stamp lands after disconnect" test below.
"""

import asyncio
from unittest.mock import patch

from asgiref.sync import async_to_sync
from django.test import TransactionTestCase
from django.utils import timezone

from gameplay.consumers import TimerConsumer
from users.models import Player
from users.tests import user_factory


class DummyChannelLayer:
    def __init__(self):
        self.groups = set()

    async def group_add(self, group, channel_name):
        self.groups.add(group)

    async def group_discard(self, group, channel_name):
        self.groups.discard(group)

    async def group_send(self, group, message):
        pass


class ConsumerHeartbeatTests(TransactionTestCase):
    def setUp(self):
        self.user = user_factory(with_player=True)
        self.player = self.user.player

    def _make_consumer(self):
        consumer = TimerConsumer()
        consumer.scope = {"user": self.user}
        consumer.channel_layer = DummyChannelLayer()
        consumer.channel_name = "test.channel.heartbeat"
        consumer.player = self.player
        consumer.player_group = f"player_{self.player.id}"
        consumer.character = None
        consumer.link = None
        consumer.activity_timer = None
        return consumer

    def _last_seen(self):
        return Player.objects.values_list("last_seen", flat=True).get(pk=self.player.pk)

    def test_the_loop_stamps_last_seen_repeatedly(self):
        consumer = self._make_consumer()

        async def run():
            # Drive it with a negligible interval rather than waiting on the
            # real 60s; the cadence is a constant, the behaviour is the loop.
            with patch("gameplay.consumers.HEARTBEAT_INTERVAL_SECONDS", 0.01):
                task = asyncio.create_task(consumer._heartbeat_loop())
                await asyncio.sleep(0.1)
                consumer._heartbeat_task = task
                await consumer._stop_heartbeat()

        Player.objects.filter(pk=self.player.pk).update(last_seen=None)

        async_to_sync(run)()

        self.assertIsNotNone(self._last_seen())

    def test_no_stamp_lands_after_the_heartbeat_is_stopped(self):
        consumer = self._make_consumer()

        async def run():
            with patch("gameplay.consumers.HEARTBEAT_INTERVAL_SECONDS", 0.01):
                consumer._heartbeat_task = asyncio.create_task(
                    consumer._heartbeat_loop()
                )
                await asyncio.sleep(0.05)
                await consumer._stop_heartbeat()

            # Anything still running would stamp during this window.
            await asyncio.sleep(0.1)

        async_to_sync(run)()
        stopped_at = self._last_seen()

        async_to_sync(asyncio.sleep)(0.05)

        self.assertEqual(self._last_seen(), stopped_at)
        self.assertIsNone(consumer._heartbeat_task)

    def test_a_failing_stamp_does_not_kill_the_loop(self):
        consumer = self._make_consumer()
        calls = []

        async def flaky():
            calls.append(1)
            if len(calls) == 1:
                raise RuntimeError("database went away")

        async def run():
            with patch(
                "gameplay.consumers.HEARTBEAT_INTERVAL_SECONDS", 0.01
            ), patch.object(consumer, "record_heartbeat", flaky):
                consumer._heartbeat_task = asyncio.create_task(
                    consumer._heartbeat_loop()
                )
                await asyncio.sleep(0.1)
                await consumer._stop_heartbeat()

        async_to_sync(run)()

        # Kept going after the failure rather than dying silently and
        # leaving the player to be swept mid-session.
        self.assertGreater(len(calls), 1)

    def test_stopping_is_safe_when_no_heartbeat_was_ever_started(self):
        consumer = self._make_consumer()

        async_to_sync(consumer._stop_heartbeat)()

    def test_record_heartbeat_advances_last_seen(self):
        consumer = self._make_consumer()
        before = timezone.now()
        Player.objects.filter(pk=self.player.pk).update(last_seen=None)

        async_to_sync(consumer.record_heartbeat)()

        self.assertGreaterEqual(self._last_seen(), before)
