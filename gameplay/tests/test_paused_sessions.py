"""
Tests for paused sessions - the state an interrupted timer lands in instead
of being force-submitted.

The guards here matter more than they look: `new_activity()` resets
elapsed_time to 0, so without them starting anything new over a paused
session would destroy the banked time rather than preserve it - making
pausing strictly worse than the auto-complete it replaced.
"""

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from gameplay.tasks import ABANDONED_PAUSE_HORIZON, complete_abandoned_paused_timers
from gameplay.utils import pause_server_timers
from progression.models import PlayerActivity
from users.tests import user_factory


class PausedSessionApiTests(TestCase):
    def setUp(self):
        self.user = user_factory(with_player=True)
        self.player = self.user.player
        self.timer = self.player.activity_timer
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def _paused_session(self, minutes=10):
        self.timer.new_activity(name="Interrupted session")
        self.timer.start()
        self.timer.start_time = timezone.now() - timedelta(minutes=minutes)
        self.timer.save(update_fields=["start_time"])
        pause_server_timers(self.timer)
        self.timer.refresh_from_db()

    def test_set_activity_refuses_to_overwrite_banked_time(self):
        self._paused_session()
        banked = self.timer.elapsed_time
        self.assertGreater(banked, 0)

        response = self.client.post(
            reverse("activitytimer-set-activity"),
            {"activityName": "Something else"},
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "paused_session_pending")
        self.timer.refresh_from_db()
        self.assertEqual(self.timer.elapsed_time, banked)

    def test_set_activity_works_once_the_session_is_discarded(self):
        self._paused_session()

        self.client.post(reverse("activitytimer-reset"), format="json")
        response = self.client.post(
            reverse("activitytimer-set-activity"),
            {"activityName": "Something else"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

    def test_resuming_within_the_sessions_own_day_is_allowed(self):
        self._paused_session()

        response = self.client.post(reverse("activitytimer-start"), format="json")

        self.assertEqual(response.status_code, 200)
        self.timer.refresh_from_db()
        self.assertEqual(self.timer.status, "active")

    def test_resuming_after_the_sessions_day_has_ended_is_refused(self):
        """
        The banked time is still the player's to submit - but continuing to
        add to it would credit today's work to the day the session began.
        """
        self._paused_session()
        activity = self.timer.activity
        activity.logical_date = activity.logical_date - timedelta(days=3)
        activity.save(update_fields=["logical_date"])

        response = self.client.post(reverse("activitytimer-start"), format="json")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "session_day_ended")
        self.timer.refresh_from_db()
        self.assertEqual(self.timer.status, "paused")

    def test_a_stale_session_can_still_be_submitted(self):
        self._paused_session()
        activity = self.timer.activity
        activity_id = activity.pk
        activity.logical_date = activity.logical_date - timedelta(days=3)
        activity.save(update_fields=["logical_date"])

        response = self.client.post(reverse("activitytimer-complete"), format="json")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(PlayerActivity.objects.get(pk=activity_id).is_complete)

    def test_a_paused_session_can_still_be_relabelled(self):
        self._paused_session()

        response = self.client.post(
            reverse("activitytimer-label-activity"),
            {"activityName": "Renamed while paused"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.timer.refresh_from_db()
        self.assertEqual(self.timer.activity.name, "Renamed while paused")

    def test_can_resume_is_reported_to_the_client(self):
        self._paused_session()

        response = self.client.post(reverse("activitytimer-pause"), format="json")

        self.assertIn("can_resume", response.data)
        self.assertTrue(response.data["can_resume"])


class AbandonedPauseJanitorTests(TestCase):
    """
    An unresolved pause blocks starting anything new, so it can't be left
    indefinitely. Completing rather than discarding delays the player's XP
    instead of losing it.
    """

    def setUp(self):
        self.user = user_factory(with_player=True)
        self.player = self.user.player
        self.timer = self.player.activity_timer

    def _paused_session(self, age):
        self.timer.new_activity(name="Abandoned session")
        self.timer.start()
        self.timer.start_time = timezone.now() - timedelta(minutes=20)
        self.timer.save(update_fields=["start_time"])
        pause_server_timers(self.timer)
        # last_updated is auto_now, so age it with an update() that bypasses
        # save() rather than trying to assign it.
        type(self.timer).objects.filter(pk=self.timer.pk).update(
            last_updated=timezone.now() - age
        )
        self.timer.refresh_from_db()

    def test_completes_a_pause_left_past_the_horizon(self):
        self._paused_session(ABANDONED_PAUSE_HORIZON + timedelta(days=1))
        activity_id = self.timer.activity_id

        result = complete_abandoned_paused_timers()

        self.assertEqual(result, 1)
        self.assertTrue(PlayerActivity.objects.get(pk=activity_id).is_complete)

    def test_credits_the_day_the_session_was_worked_not_today(self):
        self._paused_session(ABANDONED_PAUSE_HORIZON + timedelta(days=1))
        activity_id = self.timer.activity_id
        stamped = PlayerActivity.objects.get(pk=activity_id).logical_date

        complete_abandoned_paused_timers()

        self.assertEqual(
            PlayerActivity.objects.get(pk=activity_id).logical_date, stamped
        )

    def test_leaves_a_recent_pause_for_the_player_to_resolve(self):
        self._paused_session(timedelta(hours=2))

        result = complete_abandoned_paused_timers()

        self.assertEqual(result, 0)
        self.timer.refresh_from_db()
        self.assertEqual(self.timer.status, "paused")
