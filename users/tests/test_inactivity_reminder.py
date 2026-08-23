from datetime import timedelta

from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone

from core.models import GameSettings
from progression.day_boundaries import logical_date_for
from progression.models import PlayerActivity
from users.models import UserLogin
from users.services import inactivity_reminder_service
from users.tests import user_factory


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class InactivityReminderTest(TestCase):
    def setUp(self):
        GameSettings.objects.all().delete()
        self.settings = GameSettings.current()
        self.settings.inactivity_reminders_enabled_from = timezone.now() - timedelta(
            days=365
        )
        self.settings.save()

    def _anchor(self, days_ago):
        """
        A wall-clock instant `days_ago` days before today, anchored at
        midday (UTC) so it lands comfortably clear of the default 02:00
        day_start_time cutoff on either side - what matters for these
        tests is the logical date it falls on, not the exact clock time.
        """
        now = timezone.now()
        midday_today = now.replace(hour=12, minute=0, second=0, microsecond=0)
        return midday_today - timedelta(days=days_ago)

    def _inactive_user(self, email, days_ago, **extra):
        user = user_factory(email=email, with_player=True, **extra)
        stale = self._anchor(days_ago)
        login = UserLogin.objects.create(user=user)
        UserLogin.objects.filter(pk=login.pk).update(timestamp=stale)
        # `UserLogin`'s post_save signal (first-login-of-day handling) reads
        # back through `user.logins` and caches on this exact in-memory
        # `user` object before the backdate above lands - so callers must
        # not trust get_last_active_logical_date(user) on this object
        # afterwards; use the known logical date derived from `stale`
        # instead.
        return user, logical_date_for(user, stale)

    def test_sends_reminder_after_exactly_7_logical_days_inactive(self):
        self._inactive_user("stale@example.com", 7)

        with self.captureOnCommitCallbacks(execute=True):
            count = inactivity_reminder_service.send_due_reminders()

        self.assertEqual(count, 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["stale@example.com"])

    def test_no_send_before_threshold(self):
        self._inactive_user("recent@example.com", 3)

        with self.captureOnCommitCallbacks(execute=True):
            count = inactivity_reminder_service.send_due_reminders()

        self.assertEqual(count, 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_no_send_once_past_threshold(self):
        # Exactly 7 logical days is the trigger; a gap of 8+ must not fire -
        # a user's gap only reads 7 on the single day it first reaches the
        # threshold, then 8, 9, ... on every day after (see
        # send_due_reminders' docstring).
        self._inactive_user("longgone@example.com", 8)

        with self.captureOnCommitCallbacks(execute=True):
            count = inactivity_reminder_service.send_due_reminders()

        self.assertEqual(count, 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_does_not_resend_on_the_next_days_scan(self):
        # A user reminded when their gap was exactly 7 should not be
        # reminded again the next day, once the gap reads 8 - the exact-
        # equality check is what keeps a single daily scan from repeating,
        # with no separate "already sent" record needed.
        user, _last_active_date = self._inactive_user("already@example.com", 7)

        with self.captureOnCommitCallbacks(execute=True):
            inactivity_reminder_service.send_due_reminders()
        self.assertEqual(len(mail.outbox), 1)

        # A day passes with no new activity: gap is now 8, not 7.
        UserLogin.objects.filter(user=user).update(timestamp=self._anchor(8))

        with self.captureOnCommitCallbacks(execute=True):
            count = inactivity_reminder_service.send_due_reminders()

        self.assertEqual(count, 0)
        self.assertEqual(len(mail.outbox), 1)

    def test_resends_after_new_activity_starts_a_fresh_inactivity_period(self):
        user, _first_active_date = self._inactive_user("returning@example.com", 20)

        with self.captureOnCommitCallbacks(execute=True):
            inactivity_reminder_service.send_due_reminders()
        self.assertEqual(len(mail.outbox), 0)  # 20-day gap, not exactly 7

        # Came back briefly, and has now been quiet for exactly 7 more days.
        fresh_active_at = self._anchor(7)
        activity = PlayerActivity.objects.create(player=user.player, name="Back")
        PlayerActivity.objects.filter(pk=activity.pk).update(created_at=fresh_active_at)

        with self.captureOnCommitCallbacks(execute=True):
            count = inactivity_reminder_service.send_due_reminders()

        self.assertEqual(count, 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_skips_users_who_opted_out(self):
        self._inactive_user(
            "optedout@example.com", 7, receives_inactivity_reminder=False
        )

        with self.captureOnCommitCallbacks(execute=True):
            count = inactivity_reminder_service.send_due_reminders()

        self.assertEqual(count, 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_no_cutoff_set_sends_nothing(self):
        self.settings.inactivity_reminders_enabled_from = None
        self.settings.save()
        self._inactive_user("uncut@example.com", 7)

        count = inactivity_reminder_service.send_due_reminders()

        self.assertEqual(count, 0)

    def test_users_inactive_before_cutoff_are_excluded(self):
        user, _last_active_date = self._inactive_user("old@example.com", 60)
        self.settings.inactivity_reminders_enabled_from = timezone.now()
        self.settings.save()

        with self.captureOnCommitCallbacks(execute=True):
            count = inactivity_reminder_service.send_due_reminders()

        self.assertEqual(count, 0)

    def test_users_with_no_recorded_activity_are_skipped(self):
        # with_player=False and no login rows: last_active_logical_date is None.
        user_factory(email="never@example.com")

        count = inactivity_reminder_service.send_due_reminders()

        self.assertEqual(count, 0)

    def test_send_inactivity_reminders_task_delegates_and_returns_count(self):
        from users.tasks import send_inactivity_reminders

        self._inactive_user("task@example.com", 7)

        with self.captureOnCommitCallbacks(execute=True):
            result = send_inactivity_reminders.delay()

        self.assertEqual(result.get(), 1)
        self.assertEqual(len(mail.outbox), 1)
