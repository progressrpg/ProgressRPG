# gameplay/tests.py

from django.test import TestCase
from django.utils.timezone import now
import logging

from gameplay.models import (
    ServerMessage,
)

from progression.models import PlayerActivity

logging.getLogger("general").setLevel(logging.CRITICAL)

from users.tests import user_factory


class BaseTimerTest(TestCase):
    def assertTimerReset(self, timer):
        self.assertIsNone(timer.start_time)
        self.assertEqual(timer.status, "empty")
        self.assertEqual(timer.elapsed_time, 0)


class TestActivityTimer(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = user_factory(with_player=True)
        cls.player = cls.user.player
        cls.activity = PlayerActivity.objects.create(
            player=cls.player, name="Test Activity", duration=10
        )

    def setUp(self):
        self.timer = self.player.activity_timer

    def test_new_activity_sets_state(self):
        self.timer.new_activity("Test activity")
        self.assertIsInstance(self.timer.activity, PlayerActivity)
        self.assertEqual(self.timer.status, "waiting")

    def test_start_and_pause(self):
        self.timer.new_activity("Test activity")
        self.timer.start()
        self.assertEqual(self.timer.status, "active")
        self.assertIsNotNone(self.timer.start_time)

        self.timer.activity.refresh_from_db()
        self.assertIsNotNone(self.timer.activity.started_at)

        self.timer.pause()
        self.assertEqual(self.timer.status, "paused")
        self.assertIsNone(self.timer.start_time)
        self.assertGreaterEqual(self.timer.elapsed_time, 0)

    def test_reset_clears_activity(self):
        self.timer.new_activity("Test activity")
        self.timer.reset()
        self.assertIsNone(self.timer.activity)
        self.assertEqual(self.timer.status, "empty")

    def test_complete(self):
        self.timer.new_activity("Test activity")
        self.timer.elapsed_time = 15
        self.timer.start_time = now()

        activity = self.timer.activity
        xp_before = self.player.xp

        result = self.timer.complete()

        # Activity should be marked complete
        activity.refresh_from_db()
        self.assertIsNotNone(activity.completed_at)
        self.assertTrue(activity.is_complete)
        self.assertEqual(activity.duration, 15)
        self.assertEqual(activity.xp_gained, 15)

        # Player should have XP applied
        self.player.refresh_from_db()
        self.assertEqual(self.player.xp, xp_before + 15)

        self.timer.refresh_from_db()
        self.assertEqual(self.timer.status, "empty")
        self.assertIsNone(self.timer.activity)
        self.assertEqual(result["base_xp"], 15)

    def test_complete_reports_no_daily_goals_bonus_when_goals_unmet(self):
        # No UserLogin recorded for today, so the "logged in today" goal
        # isn't met and the completion bonus shouldn't fire.
        self.timer.new_activity("Test activity")
        self.timer.elapsed_time = 15
        self.timer.start_time = now()

        result = self.timer.complete()

        self.assertEqual(result["daily_goals_bonus_ap"], 0)

    def test_complete_awards_daily_goals_bonus_when_goals_met(self):
        from core.models import GameSettings
        from users.models import UserLogin

        GameSettings.current()
        settings = GameSettings.objects.get(pk=1)
        settings.daily_goals_completion_bonus_ap = 25
        settings.save(update_fields=["daily_goals_completion_bonus_ap"])
        UserLogin.objects.create(user=self.user)

        self.timer.new_activity("Test activity")
        self.timer.elapsed_time = 3 * 60
        self.timer.start_time = now()

        from progression.ap import total_ap_earned

        ap_before = total_ap_earned(self.player.level, self.player.xp)
        result = self.timer.complete()

        self.assertEqual(result["daily_goals_bonus_ap"], 25)
        self.player.refresh_from_db()
        ap_after = total_ap_earned(self.player.level, self.player.xp)
        # Lifetime AP total (level-up-proof, unlike the raw xp field, which
        # resets on level-up) went up by both the activity's own reward and
        # the daily-goals bonus.
        self.assertEqual(ap_after, ap_before + result["xp_gained"] + 25)

    def test_completing_twice_does_not_double_award_xp(self):
        """
        Two callers racing to complete the same timer - eg. the bounded-
        timer sweep and the manual /complete/ endpoint - must not both award
        XP. Simulated here with two separate in-memory ActivityTimer objects
        for the same row, since Django's TestCase can't exercise real
        concurrent transactions.
        """
        from gameplay.models import ActivityTimer

        self.timer.new_activity("Test activity")
        self.timer.elapsed_time = 15
        self.timer.start_time = now()
        self.timer.save(update_fields=["elapsed_time", "start_time"])

        racing_timer = ActivityTimer.objects.get(pk=self.timer.pk)
        xp_before = self.player.xp

        first_result = self.timer.complete()
        second_result = racing_timer.complete()

        self.assertGreater(first_result["xp_gained"], 0)
        self.assertEqual(second_result["xp_gained"], 0)
        self.assertEqual(second_result["level_ups"], [])

        self.player.refresh_from_db()
        self.assertEqual(self.player.xp, xp_before + first_result["xp_gained"])


class TestServerMessageModel(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = user_factory(with_player=True)
        cls.player = cls.user.player

    def test_server_message_create(self):
        message = ServerMessage.objects.create(
            group=self.player.group_name,
            type="notification",
            action="quest_complete",
            data={"quest_id": 1},
            message="Quest completed successfully!",
            is_draft=False,
        )
        self.assertTrue(isinstance(message, ServerMessage))
        self.assertEqual(message.type, "notification")
        self.assertEqual(message.action, "quest_complete")
        self.assertEqual(message.data["quest_id"], 1)
        self.assertFalse(message.is_delivered)

    def test_server_message_mark_delivered(self):
        message = ServerMessage.objects.create(
            group=self.player.group_name,
            type="notification",
            action="quest_complete",
            data={"quest_id": 1},
            message="Quest completed successfully!",
            is_draft=False,
        )
        message.mark_delivered()
        self.assertTrue(message.is_delivered)
