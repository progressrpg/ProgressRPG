from asgiref.sync import async_to_sync
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.test import SimpleTestCase, TransactionTestCase

from character.models import PlayerCharacterLink
from gameplay.consumers import TimerConsumer
from users.tests import user_factory


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


class TimerConsumerNoCharacterTests(TransactionTestCase):
    def setUp(self):
        # The online-count cache is shared real Redis state across tests;
        # clear it so a value cached by another test doesn't leak in here.
        cache.clear()
        self.user = user_factory(with_player=True)
        self.player = self.user.player

        # Ensure this test user has no active player-character link.
        PlayerCharacterLink.objects.filter(player=self.player, is_active=True).update(
            is_active=False
        )

    def test_connect_accepts_without_active_character(self):
        consumer = TimerConsumer()

        # set_player_and_character in isolation, before exercising the full
        # connect() flow below.
        player, character, link = async_to_sync(consumer.set_player_and_character)(
            self.user
        )
        self.assertEqual(player, self.player)
        self.assertIsNone(character)
        self.assertIsNone(link)

        consumer.scope = {"user": self.user}
        consumer.channel_layer = DummyChannelLayer()
        consumer.channel_name = "test.channel.no.character"

        accept_recorder = AsyncCallRecorder()
        close_recorder = AsyncCallRecorder()
        send_json_recorder = AsyncCallRecorder()
        pending_recorder = AsyncCallRecorder()
        timer_recorder = AsyncCallRecorder(return_value=None)

        consumer.accept = accept_recorder
        consumer.close = close_recorder
        consumer.send_json = send_json_recorder
        consumer._send_pending_messages = pending_recorder
        consumer.get_activity_timer = timer_recorder

        async_to_sync(consumer.connect)()

        self.assertEqual(len(accept_recorder.calls), 1)
        self.assertEqual(len(close_recorder.calls), 0)
        self.assertEqual(consumer.player, self.player)
        self.assertIsNone(consumer.character)
        self.assertIsNone(consumer.link)

        self.player.refresh_from_db(fields=["active_connections", "is_online"])
        self.assertEqual(self.player.active_connections, 1)
        self.assertTrue(self.player.is_online)

        sent_payloads = [args[0] for args, _ in send_json_recorder.calls]
        self.assertIn(
            {
                "type": "server_message",
                "action": "no_active_character",
                "message": "Connected without an active character.",
            },
            sent_payloads,
        )

        group_messages = consumer.channel_layer.group_messages
        self.assertEqual(len(group_messages), 1)
        self.assertEqual(group_messages[0][0], "online_users")
        self.assertEqual(group_messages[0][1]["type"], "online_count")
        self.assertEqual(group_messages[0][1]["count"], 1)


class TimerConsumerAuthTests(SimpleTestCase):
    """
    Tests for connect() when the JWT is missing or expired.
    The middleware sets AnonymousUser on the scope in both cases,
    so the consumer must close without accepting.
    """

    def _make_consumer(self, user):
        consumer = TimerConsumer()
        consumer.scope = {"user": user}
        consumer.channel_layer = DummyChannelLayer()
        consumer.channel_name = "test.channel.auth"
        consumer.accept = AsyncCallRecorder()
        consumer.close = AsyncCallRecorder()
        return consumer

    def test_connect_closes_when_user_is_anonymous(self):
        consumer = self._make_consumer(AnonymousUser())

        async_to_sync(consumer.connect)()

        self.assertEqual(len(consumer.close.calls), 1)
        self.assertEqual(len(consumer.accept.calls), 0)

    def test_connect_closes_when_scope_has_no_user(self):
        consumer = TimerConsumer()
        consumer.scope = {}  # middleware absent / misconfigured
        consumer.channel_layer = DummyChannelLayer()
        consumer.channel_name = "test.channel.no-user"
        consumer.accept = AsyncCallRecorder()
        consumer.close = AsyncCallRecorder()

        async_to_sync(consumer.connect)()

        self.assertEqual(len(consumer.close.calls), 1)
        self.assertEqual(len(consumer.accept.calls), 0)


class TimerConsumerDisconnectTests(TransactionTestCase):
    def setUp(self):
        cache.clear()
        self.user = user_factory(with_player=True)
        self.player = self.user.player

    def _make_connected_consumer(self):
        consumer = TimerConsumer()
        consumer.scope = {"user": self.user}
        consumer.channel_layer = DummyChannelLayer()
        consumer.channel_name = "test.channel.disconnect"
        consumer.player = self.player
        consumer.player_group = f"player_{self.player.id}"
        consumer.character = None
        consumer.link = None
        consumer.activity_timer = MockTimer(status="empty")
        # Simulate the groups that connect() would have joined.
        async_to_sync(consumer.channel_layer.group_add)(
            consumer.player_group, consumer.channel_name
        )
        async_to_sync(consumer.channel_layer.group_add)(
            "online_users", consumer.channel_name
        )
        return consumer

    def test_disconnect_returns_early_without_player(self):
        """No player means an unauthenticated socket was closed — skip all cleanup."""
        consumer = TimerConsumer()
        consumer.scope = {"user": AnonymousUser()}
        consumer.channel_layer = DummyChannelLayer()
        consumer.channel_name = "test.channel.anon-disconnect"

        async_to_sync(consumer.disconnect)(1000)

        self.assertEqual(len(consumer.channel_layer.groups), 0)

    def test_disconnect_removes_player_from_groups_and_broadcasts_online_count(self):
        consumer = self._make_connected_consumer()

        self.assertIn(consumer.player_group, consumer.channel_layer.groups)
        self.assertIn("online_users", consumer.channel_layer.groups)

        self.player.active_connections = 1
        self.player.is_online = True
        self.player.save(update_fields=["active_connections", "is_online"])

        async_to_sync(consumer.disconnect)(1000)

        self.assertNotIn(consumer.player_group, consumer.channel_layer.groups)
        self.assertNotIn("online_users", consumer.channel_layer.groups)

        group_messages = consumer.channel_layer.group_messages
        self.assertEqual(len(group_messages), 1)
        self.assertEqual(group_messages[0][0], "online_users")
        self.assertEqual(group_messages[0][1]["type"], "online_count")
        self.assertEqual(group_messages[0][1]["count"], 0)

    def test_disconnect_keeps_player_online_with_other_connections(self):
        consumer = self._make_connected_consumer()

        self.player.active_connections = 2
        self.player.is_online = True
        self.player.save(update_fields=["active_connections", "is_online"])

        async_to_sync(consumer.disconnect)(1000)

        self.player.refresh_from_db(fields=["active_connections", "is_online"])
        self.assertEqual(self.player.active_connections, 1)
        self.assertTrue(self.player.is_online)

    def test_disconnect_does_not_pause_timers_when_already_paused(self):
        """Timer in a terminal state must not trigger control_timers."""
        consumer = self._make_connected_consumer()
        consumer.activity_timer = MockTimer(status="paused")

        # If control_timers were called it would hit the DB and raise; passing
        # without error is the assertion.
        async_to_sync(consumer.disconnect)(1000)


class TimerConsumerOnlineCountEventTests(SimpleTestCase):
    def test_online_count_event_sends_payload(self):
        consumer = TimerConsumer()
        consumer.send_json = AsyncCallRecorder()

        async_to_sync(consumer.online_count)({"type": "online_count", "count": 7})

        self.assertEqual(len(consumer.send_json.calls), 1)
        sent_payload = consumer.send_json.calls[0][0][0]
        self.assertEqual(sent_payload, {"type": "online_count", "count": 7})


class TimerConsumerHeartbeatTests(TransactionTestCase):
    """A client 'ping' must refresh Player.last_seen so
    reconcile_stale_online_players doesn't sweep up live connections."""

    def setUp(self):
        self.user = user_factory(with_player=True)
        self.player = self.user.player

    def test_ping_refreshes_last_seen(self):
        consumer = TimerConsumer()
        consumer.player = self.player
        consumer.send_json = AsyncCallRecorder()

        self.assertIsNone(self.player.last_seen)

        async_to_sync(consumer.receive_json)({"type": "ping"})

        self.player.refresh_from_db(fields=["last_seen"])
        self.assertIsNotNone(self.player.last_seen)

        sent_payloads = [args[0] for args, _ in consumer.send_json.calls]
        self.assertIn(
            {"type": "pong", "action": "pong", "message": "pong"}, sent_payloads
        )
