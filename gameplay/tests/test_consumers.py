from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from django.test import TestCase

from character.models import PlayerCharacterLink
from gameplay.consumers import TimerConsumer


class DummyChannelLayer:
    def __init__(self):
        self.groups = set()

    async def group_add(self, group, channel_name):
        self.groups.add(group)

    async def group_discard(self, group, channel_name):
        self.groups.discard(group)


class AsyncCallRecorder:
    def __init__(self, return_value=None):
        self.calls = []
        self.return_value = return_value

    async def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.return_value


class TimerConsumerNoCharacterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            email="ws-no-character@example.com",
            password="test-pass-123",
        )
        cls.player = cls.user.player

        # Ensure this test user has no active player-character link.
        PlayerCharacterLink.objects.filter(player=cls.player, is_active=True).update(
            is_active=False
        )

    def test_set_player_and_character_handles_missing_link(self):
        consumer = TimerConsumer()

        player, character, link = async_to_sync(consumer.set_player_and_character)(
            self.user
        )

        self.assertEqual(player, self.player)
        self.assertIsNone(character)
        self.assertIsNone(link)

    def test_connect_accepts_without_active_character(self):
        consumer = TimerConsumer()
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

        sent_payloads = [args[0] for args, _ in send_json_recorder.calls]
        self.assertIn(
            {
                "type": "server_message",
                "action": "no_active_character",
                "message": "Connected without an active character.",
            },
            sent_payloads,
        )
