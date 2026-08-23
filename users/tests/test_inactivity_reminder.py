from datetime import timedelta

from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone

from core.models import GameSettings
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

    def _inactive_user(self, email, days_ago, **extra):
        user = user_factory(email=email, with_player=True, **extra)
        stale = timezone.now() - timedelta(days=days_ago)
        login = UserLogin.objects.create(user=user)
        UserLogin.objects.filter(pk=login.pk).update(timestamp=stale)
        return user

    def test_sends_reminder_after_7_days_inactive_and_marks_sent(self):
        user = self._inactive_user("stale@example.com", 7)

        with self.captureOnCommitCallbacks(execute=True):
            count = inactivity_reminder_service.send_due_reminders()

        user.refresh_from_db()
        self.assertEqual(count, 1)
        self.assertIsNotNone(user.inactivity_reminder_sent_at)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["stale@example.com"])

    def test_no_send_before_threshold(self):
        user = self._inactive_user("recent@example.com", 3)

        with self.captureOnCommitCallbacks(execute=True):
            count = inactivity_reminder_service.send_due_reminders()

        user.refresh_from_db()
        self.assertEqual(count, 0)
        self.assertIsNone(user.inactivity_reminder_sent_at)
        self.assertEqual(len(mail.outbox), 0)

    def test_does_not_resend_within_same_inactivity_period(self):
        user = self._inactive_user("already@example.com", 7)
        user.inactivity_reminder_sent_at = timezone.now()
        user.save(update_fields=["inactivity_reminder_sent_at"])

        with self.captureOnCommitCallbacks(execute=True):
            count = inactivity_reminder_service.send_due_reminders()

        self.assertEqual(count, 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_resends_after_new_activity_starts_a_fresh_inactivity_period(self):
        user = self._inactive_user("returning@example.com", 20)
        # Reminded for the first inactivity period...
        user.inactivity_reminder_sent_at = timezone.now() - timedelta(days=13)
        user.save(update_fields=["inactivity_reminder_sent_at"])
        # ...then came back briefly, and has now been quiet for 7 more days.
        activity = PlayerActivity.objects.create(player=user.player, name="Back")
        PlayerActivity.objects.filter(pk=activity.pk).update(
            created_at=timezone.now() - timedelta(days=7)
        )

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
        user = self._inactive_user("old@example.com", 60)
        self.settings.inactivity_reminders_enabled_from = timezone.now()
        self.settings.save()

        with self.captureOnCommitCallbacks(execute=True):
            count = inactivity_reminder_service.send_due_reminders()

        user.refresh_from_db()
        self.assertEqual(count, 0)
        self.assertIsNone(user.inactivity_reminder_sent_at)

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
