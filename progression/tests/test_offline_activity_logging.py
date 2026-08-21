"""Tests for manually logging completed activities after the fact
(offline logging, issue #630).

Covers:
- ``progression.services.log_offline_activity`` XP eligibility rules
  (premium-only, 7-day backdating cliff, daily XP/duration caps)
- Double-dip prevention via the append-only ``OfflineActivityLedger``
- The ``player-activities/log_offline/`` API endpoint
"""

from datetime import datetime, time, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from payments.models import SubscriptionPlan, UserSubscription
from progression.models import OfflineActivityLedger, PlayerActivity, PlayerSkill, Task
from progression.services import (
    OFFLINE_DAILY_XP_ELIGIBLE_CAP_SECONDS,
    log_offline_activity,
)

from progression.day_boundaries import (
    current_logical_date,
    logical_date_for,
    logical_day_bounds,
)
from users.tests import user_factory


def past_logical_day_start(player, days_ago: int = 1):
    """Return the start instant of a past *logical* day for `player`.

    Anchoring on the logical day rather than local midnight is what keeps
    the daily-cap tests deterministic: with a day_start_time cutoff, local
    midnight belongs to the previous logical day, so a run anchored there
    would spill its later hours into the next day's ledger and never hit
    the cap under test.
    """
    day = current_logical_date(player) - timedelta(days=days_ago)
    start, _end = logical_day_bounds(player, day)
    return start


class OfflineLoggingTestBase(TestCase):
    def setUp(self):
        self.user = user_factory(with_player=True)
        self.player = self.user.player

    def grant_premium(self):
        UserSubscription.deactivate_all_for_user(self.user)
        plan = SubscriptionPlan.objects.create(
            name="Premium Monthly",
            description="",
            price="9.99",
            interval="monthly",
            stripe_price_id=f"price_{self.user.id}",
        )
        return UserSubscription.objects.create(
            user=self.user,
            plan=plan,
            active=True,
            stripe_subscription_id=f"sub_{self.user.id}",
        )


class LogOfflineActivityServiceTests(OfflineLoggingTestBase):
    def test_free_user_records_activity_with_zero_xp(self):
        completed_at = timezone.now() - timedelta(hours=1)
        started_at = completed_at - timedelta(hours=1)

        result = log_offline_activity(
            self.player,
            name="Evening run",
            started_at=started_at,
            completed_at=completed_at,
        )

        self.assertEqual(result.activity.duration, 3600)
        self.assertEqual(result.activity.origin, PlayerActivity.Origin.MANUAL)
        self.assertTrue(result.activity.is_complete)
        self.assertEqual(result.activity.xp_gained, 0)
        self.assertEqual(result.xp_eligible_seconds, 0)
        self.assertIsNotNone(result.activity.task_id)

    def test_premium_user_within_cliff_earns_xp(self):
        self.grant_premium()
        completed_at = timezone.now() - timedelta(hours=1)
        started_at = completed_at - timedelta(hours=1)

        result = log_offline_activity(
            self.player,
            name="Deep work",
            started_at=started_at,
            completed_at=completed_at,
        )

        self.assertEqual(result.xp_eligible_seconds, 3600)
        self.assertGreater(result.activity.xp_gained, 0)
        self.assertEqual(result.activity.xp_gained, result.reward_summary["xp_gained"])

    def test_premium_user_beyond_backdate_cliff_earns_zero_xp(self):
        self.grant_premium()
        completed_at = timezone.now() - timedelta(days=8)
        started_at = completed_at - timedelta(hours=1)

        result = log_offline_activity(
            self.player,
            name="Old chores",
            started_at=started_at,
            completed_at=completed_at,
        )

        self.assertEqual(result.xp_eligible_seconds, 0)
        self.assertEqual(result.activity.xp_gained, 0)
        # Still recorded for completeness/history.
        self.assertEqual(result.activity.duration, 3600)
        self.assertTrue(result.activity.is_complete)

    def test_daily_duration_cap_enforced_regardless_of_tier(self):
        self.grant_premium()
        base = past_logical_day_start(self.player)

        log_offline_activity(
            self.player,
            name="Long session",
            started_at=base,
            completed_at=base + timedelta(hours=15),
        )

        with self.assertRaises(ValidationError):
            log_offline_activity(
                self.player,
                name="Pushes over cap",
                started_at=base + timedelta(hours=15),
                completed_at=base + timedelta(hours=17),
            )

    def test_daily_xp_eligible_cap_limits_premium_xp_not_duration(self):
        self.grant_premium()
        base = past_logical_day_start(self.player)

        first = log_offline_activity(
            self.player,
            name="First block",
            started_at=base,
            completed_at=base + timedelta(hours=5),
        )
        self.assertEqual(first.xp_eligible_seconds, 5 * 3600)

        second = log_offline_activity(
            self.player,
            name="Second block",
            started_at=base + timedelta(hours=5),
            completed_at=base + timedelta(hours=8),
        )

        # Only 1 more hour is eligible before the 6h/day XP cap is hit...
        self.assertEqual(second.xp_eligible_seconds, 1 * 3600)
        # ...but the full 3h duration is still recorded.
        self.assertEqual(second.activity.duration, 3 * 3600)

        ledger = OfflineActivityLedger.objects.get(
            player=self.player, date=logical_date_for(self.player, base)
        )
        self.assertEqual(
            ledger.xp_eligible_seconds, OFFLINE_DAILY_XP_ELIGIBLE_CAP_SECONDS
        )
        self.assertEqual(ledger.logged_seconds, 8 * 3600)

    def test_deleting_activity_does_not_reset_ledger(self):
        """Ledger rows are append-only, so delete-then-relog can't double-dip."""
        self.grant_premium()
        base = timezone.now() - timedelta(hours=8)

        first = log_offline_activity(
            self.player,
            name="Will be deleted",
            started_at=base,
            completed_at=base + timedelta(hours=6),
        )
        self.assertEqual(
            first.xp_eligible_seconds, OFFLINE_DAILY_XP_ELIGIBLE_CAP_SECONDS
        )
        first.activity.delete()

        second = log_offline_activity(
            self.player,
            name="Re-logged after delete",
            started_at=base,
            completed_at=base + timedelta(hours=1),
        )

        self.assertEqual(second.xp_eligible_seconds, 0)
        self.assertEqual(second.activity.xp_gained, 0)

    def test_completed_at_before_started_at_rejected(self):
        now = timezone.now()
        with self.assertRaises(ValidationError):
            log_offline_activity(
                self.player,
                name="Bad window",
                started_at=now,
                completed_at=now - timedelta(hours=1),
            )

    def test_future_completed_at_rejected(self):
        now = timezone.now()
        with self.assertRaises(ValidationError):
            log_offline_activity(
                self.player,
                name="From the future",
                started_at=now,
                completed_at=now + timedelta(hours=1),
            )

    def test_attaches_to_existing_task_without_creating_new_one(self):
        task = Task.objects.create(player=self.player, name="Existing task")
        completed_at = timezone.now() - timedelta(hours=1)
        started_at = completed_at - timedelta(minutes=30)

        result = log_offline_activity(
            self.player,
            name="",
            task=task,
            started_at=started_at,
            completed_at=completed_at,
        )

        self.assertEqual(result.activity.task_id, task.id)
        self.assertEqual(Task.objects.filter(player=self.player).count(), 1)

    def test_uses_same_xp_multiplier_rules_as_timer_completion(self):
        """XP for the eligible portion matches get_xp_reward_summary directly."""
        self.grant_premium()
        completed_at = timezone.now() - timedelta(hours=1)
        started_at = completed_at - timedelta(minutes=10)

        result = log_offline_activity(
            self.player,
            name="Check multiplier reuse",
            started_at=started_at,
            completed_at=completed_at,
        )

        expected = result.activity.get_xp_reward_summary(duration=600)
        self.assertEqual(result.activity.xp_gained, expected["xp_gained"])

    def test_offline_logging_can_clear_daily_goals(self):
        """Offline-logged activities count toward the daily-goals badge
        (issue #751) the same as timer-based completions - both are player
        activity completions."""
        from users.models import UserLogin

        from progression.daily_goals import MINUTES_GOAL_THRESHOLD
        from progression.models import DailyGoalAward

        UserLogin.objects.create(user=self.user)
        completed_at = timezone.now() - timedelta(minutes=5)
        started_at = completed_at - timedelta(minutes=MINUTES_GOAL_THRESHOLD)

        log_offline_activity(
            self.player,
            name="Evening chores",
            started_at=started_at,
            completed_at=completed_at,
        )

        self.assertTrue(
            DailyGoalAward.objects.filter(
                player=self.player, date=current_logical_date(self.player)
            ).exists()
        )


class PlayerActivityLogOfflineApiTests(APITestCase):
    def setUp(self):
        self.user = user_factory(with_player=True)
        self.player = self.user.player
        self.other_user = user_factory(with_player=True)
        self.client.force_authenticate(user=self.user)

    def _log(self, **overrides):
        completed_at = timezone.now() - timedelta(hours=1)
        started_at = completed_at - timedelta(minutes=45)
        payload = {
            "name": "Read a book",
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
        }
        payload.update(overrides)
        return self.client.post(reverse("playeractivity-log-offline"), payload)

    def test_logs_activity_and_creates_task(self):
        response = self._log()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["activity"]["origin"], "manual")
        activity = PlayerActivity.objects.get(pk=response.data["activity"]["id"])
        self.assertIsNotNone(activity.task_id)
        self.assertEqual(activity.task.player, self.player)

    def test_missing_name_and_task_is_rejected(self):
        response = self._log(name="")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_log_against_another_players_task(self):
        other_task = Task.objects.create(player=self.other_user.player, name="Theirs")

        response = self._log(name="", task=other_task.id)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_use_another_players_skill(self):
        other_skill = PlayerSkill.objects.create(
            player=self.other_user.player, name="Their skill"
        )

        response = self._log(skill=other_skill.id)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_exceeding_daily_cap_returns_400(self):
        base = past_logical_day_start(self.player)
        self._log(
            name="First",
            started_at=base.isoformat(),
            completed_at=(base + timedelta(hours=15)).isoformat(),
        )

        response = self._log(
            name="Second",
            started_at=(base + timedelta(hours=15)).isoformat(),
            completed_at=(base + timedelta(hours=17)).isoformat(),
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_generic_create_endpoint_cannot_set_origin_manual(self):
        """``origin`` is read-only on the generic create path — only the
        offline-logging service (with its cap/eligibility checks) may set
        it to "manual"."""
        response = self.client.post(
            reverse("playeractivity-list"),
            {"name": "Direct create", "duration": 60, "origin": "manual"},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        activity = PlayerActivity.objects.get(pk=response.data["activity"]["id"])
        self.assertEqual(activity.origin, PlayerActivity.Origin.TIMER)
