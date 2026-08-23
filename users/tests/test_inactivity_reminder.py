from datetime import timedelta

from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone

from core.models import GameSettings
from progression.models import PlayerActivity
from users.models import ReminderLog, UserLogin
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

    def _inactive_user(self, email, days_ago, **extra):
        user = user_factory(email=email, with_player=True, **extra)
        stale = timezone.now() - timedelta(days=days_ago)
        login = UserLogin.objects.create(user=user)
        UserLogin.objects.filter(pk=login.pk).update(timestamp=stale)
        # `UserLogin`'s post_save signal (first-login-of-day handling) reads
        # back through `user.logins` and caches on this exact in-memory
        # `user` object before the backdate above lands - so callers must
        # not trust get_last_active_at(user) on this object afterwards; use
        # the known `stale` instant instead (see
        # test_does_not_resend_within_same_inactivity_period and friends).
        return user, stale

    def _log_reminder(self, user, triggered_by_activity_at):
        return ReminderLog.objects.create(
            user=user,
            reminder_type=ReminderLog.ReminderType.INACTIVITY_7DAY,
            triggered_by_activity_at=triggered_by_activity_at,
        )

    def test_sends_reminder_after_7_days_inactive_and_logs_it(self):
        user, stale = self._inactive_user("stale@example.com", 7)

        with self.captureOnCommitCallbacks(execute=True):
            count = inactivity_reminder_service.send_due_reminders()

        self.assertEqual(count, 1)
        self.assertTrue(
            ReminderLog.objects.filter(
                user=user,
                reminder_type=ReminderLog.ReminderType.INACTIVITY_7DAY,
                triggered_by_activity_at=stale,
            ).exists()
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["stale@example.com"])

    def test_no_send_before_threshold(self):
        user, _stale = self._inactive_user("recent@example.com", 3)

        with self.captureOnCommitCallbacks(execute=True):
            count = inactivity_reminder_service.send_due_reminders()

        self.assertEqual(count, 0)
        self.assertFalse(ReminderLog.objects.filter(user=user).exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_does_not_resend_within_same_inactivity_period(self):
        user, stale = self._inactive_user("already@example.com", 7)
        self._log_reminder(user, stale)

        with self.captureOnCommitCallbacks(execute=True):
            count = inactivity_reminder_service.send_due_reminders()

        self.assertEqual(count, 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_resends_after_new_activity_starts_a_fresh_inactivity_period(self):
        user, _stale = self._inactive_user("returning@example.com", 20)
        # Reminded for the first inactivity period...
        self._log_reminder(user, timezone.now() - timedelta(days=20))
        # ...then came back briefly, and has now been quiet for 7 more days.
        activity = PlayerActivity.objects.create(player=user.player, name="Back")
        PlayerActivity.objects.filter(pk=activity.pk).update(
            created_at=timezone.now() - timedelta(days=7)
        )

        with self.captureOnCommitCallbacks(execute=True):
            count = inactivity_reminder_service.send_due_reminders()

        self.assertEqual(count, 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            ReminderLog.objects.filter(
                user=user, reminder_type=ReminderLog.ReminderType.INACTIVITY_7DAY
            ).count(),
            2,
        )

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
        user, _stale = self._inactive_user("old@example.com", 60)
        self.settings.inactivity_reminders_enabled_from = timezone.now()
        self.settings.save()

        with self.captureOnCommitCallbacks(execute=True):
            count = inactivity_reminder_service.send_due_reminders()

        self.assertEqual(count, 0)
        self.assertFalse(ReminderLog.objects.filter(user=user).exists())

    def test_users_with_no_recorded_activity_are_skipped(self):
        # with_player=False and no login rows: last_active_at is None.
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
