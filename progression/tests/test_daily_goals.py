"""Tests for the map-view "daily goals" badge (issue #751, replacing the
old `points_today` mechanic from issue #673).

Covers:
- ``progression.daily_goals.get_daily_goals_state`` goal computation
- ``progression.daily_goals.check_and_award_daily_goals`` idempotent bonus
  award
"""

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from character.models import Character, PlayerCharacterLink
from core.models import GameSettings
from progression.daily_goals import (
    MINUTES_GOAL_THRESHOLD,
    check_and_award_daily_goals,
    get_daily_goals_state,
)
from progression.models import DailyGoalAward, PlayerActivity
from users.models import UserLogin
from users.tests import user_factory


class DailyGoalsTestBase(TestCase):
    def setUp(self):
        self.user = user_factory(with_player=True)
        self.player = self.user.player
        self.character = Character.objects.create(given_name="Hero")
        PlayerCharacterLink.objects.create(player=self.player, character=self.character)

    def complete_activity(self, minutes: int):
        return PlayerActivity.objects.create(
            player=self.player,
            is_complete=True,
            duration=minutes * 60,
            completed_at=timezone.now(),
        )


class GetDailyGoalsStateTests(DailyGoalsTestBase):
    def test_all_false_with_no_login_or_activity(self):
        state = get_daily_goals_state(self.player)

        self.assertFalse(state.logged_in_today)
        self.assertFalse(state.completed_activity_today)
        self.assertEqual(state.activity_minutes_today, 0)
        self.assertFalse(state.minutes_goal_met)
        self.assertFalse(state.all_goals_met)
        self.assertFalse(state.bonus_awarded_today)
        self.assertEqual(state.bonus_ap, 0)

    def test_logged_in_today_reflects_userlogin(self):
        UserLogin.objects.create(user=self.user)

        state = get_daily_goals_state(self.player)

        self.assertTrue(state.logged_in_today)
        self.assertFalse(state.all_goals_met)

    def test_activity_below_threshold_does_not_meet_minutes_goal(self):
        self.complete_activity(MINUTES_GOAL_THRESHOLD - 1)

        state = get_daily_goals_state(self.player)

        self.assertTrue(state.completed_activity_today)
        self.assertFalse(state.minutes_goal_met)

    def test_activity_at_threshold_meets_minutes_goal(self):
        self.complete_activity(MINUTES_GOAL_THRESHOLD)

        state = get_daily_goals_state(self.player)

        self.assertTrue(state.minutes_goal_met)

    def test_several_short_activities_accumulate_toward_minutes_goal(self):
        for _ in range(MINUTES_GOAL_THRESHOLD):
            self.complete_activity(1)

        state = get_daily_goals_state(self.player)

        self.assertEqual(state.activity_minutes_today, MINUTES_GOAL_THRESHOLD)
        self.assertTrue(state.minutes_goal_met)

    def test_incomplete_activity_not_counted(self):
        PlayerActivity.objects.create(
            player=self.player,
            is_complete=False,
            duration=600,
        )

        state = get_daily_goals_state(self.player)

        self.assertFalse(state.completed_activity_today)
        self.assertEqual(state.activity_minutes_today, 0)

    def test_yesterdays_activity_not_counted(self):
        yesterday = timezone.now() - timedelta(days=1, hours=1)
        PlayerActivity.objects.create(
            player=self.player,
            is_complete=True,
            duration=600,
            completed_at=yesterday,
        )

        state = get_daily_goals_state(self.player, today=timezone.localdate())

        self.assertFalse(state.completed_activity_today)

    def test_all_goals_met_when_logged_in_and_activity_clears_minutes(self):
        UserLogin.objects.create(user=self.user)
        self.complete_activity(MINUTES_GOAL_THRESHOLD)

        state = get_daily_goals_state(self.player)

        self.assertTrue(state.all_goals_met)

    def test_reflects_existing_award_row(self):
        today = timezone.localdate()
        DailyGoalAward.objects.create(player=self.player, date=today, bonus_ap=42)

        state = get_daily_goals_state(self.player, today=today)

        self.assertTrue(state.bonus_awarded_today)
        self.assertEqual(state.bonus_ap, 42)


class CheckAndAwardDailyGoalsTests(DailyGoalsTestBase):
    def test_no_award_when_goals_not_met(self):
        state, level_ups = check_and_award_daily_goals(self.player)

        self.assertFalse(state.all_goals_met)
        self.assertEqual(level_ups, [])
        self.assertFalse(DailyGoalAward.objects.filter(player=self.player).exists())

    def test_awards_configured_bonus_when_all_goals_met(self):
        settings = GameSettings.current()
        settings.daily_goals_completion_bonus_ap = 30
        settings.save(update_fields=["daily_goals_completion_bonus_ap"])

        UserLogin.objects.create(user=self.user)
        self.complete_activity(MINUTES_GOAL_THRESHOLD)

        starting_xp = self.player.xp
        state, _level_ups = check_and_award_daily_goals(self.player)

        self.assertTrue(state.all_goals_met)
        self.assertTrue(state.bonus_awarded_today)
        self.assertEqual(state.bonus_ap, 30)

        self.player.refresh_from_db()
        self.assertEqual(self.player.xp, starting_xp + 30)

        award = DailyGoalAward.objects.get(
            player=self.player, date=timezone.localdate()
        )
        self.assertEqual(award.bonus_ap, 30)

    def test_bonus_not_awarded_twice_in_the_same_day(self):
        settings = GameSettings.current()
        settings.daily_goals_completion_bonus_ap = 30
        settings.save(update_fields=["daily_goals_completion_bonus_ap"])

        UserLogin.objects.create(user=self.user)
        self.complete_activity(MINUTES_GOAL_THRESHOLD)

        check_and_award_daily_goals(self.player)
        self.player.refresh_from_db()
        xp_after_first_award = self.player.xp

        self.complete_activity(MINUTES_GOAL_THRESHOLD)
        state, level_ups = check_and_award_daily_goals(self.player)

        self.assertEqual(level_ups, [])
        self.assertEqual(state.bonus_ap, 30)
        self.player.refresh_from_db()
        self.assertEqual(self.player.xp, xp_after_first_award)
        self.assertEqual(DailyGoalAward.objects.filter(player=self.player).count(), 1)

    def test_returns_level_ups_when_bonus_crosses_a_level(self):
        settings = GameSettings.current()
        settings.daily_goals_completion_bonus_ap = 1000
        settings.save(update_fields=["daily_goals_completion_bonus_ap"])

        UserLogin.objects.create(user=self.user)
        self.complete_activity(MINUTES_GOAL_THRESHOLD)

        _state, level_ups = check_and_award_daily_goals(self.player)

        self.assertTrue(level_ups)
