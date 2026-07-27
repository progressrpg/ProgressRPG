from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import GameSettings
from users.models import InviteCode, Waitlist
from users.services import waitlist_service

User = get_user_model()


class RegistrationStatusAPITest(APITestCase):
    def setUp(self):
        GameSettings.objects.all().delete()
        self.settings = GameSettings.current()

    def test_registration_open_below_cap(self):
        self.settings.registration_cap = 100
        self.settings.save()
        res = self.client.get("/api/v1/registration_status/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.json()["registration_open"])

    def test_registration_closed_at_cap(self):
        user = User.objects.create_user(
            email="a@example.com", password="testpassword123"
        )
        user.is_confirmed = True
        user.save(update_fields=["is_confirmed"])
        self.settings.registration_cap = User.objects.count()
        self.settings.save()
        res = self.client.get("/api/v1/registration_status/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(res.json()["registration_open"])

    def test_registration_open_ignores_unconfirmed_users_at_cap(self):
        User.objects.create_user(email="a@example.com", password="testpassword123")
        self.settings.registration_cap = User.objects.count()
        self.settings.save()
        res = self.client.get("/api/v1/registration_status/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.json()["registration_open"])

    def test_endpoint_requires_no_auth(self):
        res = self.client.get("/api/v1/registration_status/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_registration_enabled_reported_true_by_default(self):
        res = self.client.get("/api/v1/registration_status/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.json()["registration_enabled"])

    def test_registration_enabled_reported_false_when_killed(self):
        self.settings.registration_enabled = False
        self.settings.save()
        res = self.client.get("/api/v1/registration_status/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(res.json()["registration_enabled"])

    def test_self_serve_registration_reported_false_by_default(self):
        res = self.client.get("/api/v1/registration_status/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(res.json()["self_serve_registration"])

    def test_self_serve_registration_reported_true_when_enabled(self):
        self.settings.self_serve_registration = True
        self.settings.save()
        res = self.client.get("/api/v1/registration_status/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.json()["self_serve_registration"])

    def test_turnstile_site_key_reported_when_configured(self):
        with override_settings(CF_TURNSTILE_SITE_KEY="0x-site-key"):
            res = self.client.get("/api/v1/registration_status/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.json()["turnstile_site_key"], "0x-site-key")

    def test_turnstile_site_key_blank_when_unconfigured(self):
        with override_settings(CF_TURNSTILE_SITE_KEY=None):
            res = self.client.get("/api/v1/registration_status/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.json()["turnstile_site_key"], "")

    def test_waitlist_signup_provider_defaults_to_mailchimp(self):
        res = self.client.get("/api/v1/registration_status/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.json()["waitlist_signup_provider"], "mailchimp")

    def test_waitlist_signup_provider_reports_internal_when_set(self):
        self.settings.waitlist_signup_provider = GameSettings.WaitlistSignupProvider.INTERNAL
        self.settings.save()
        res = self.client.get("/api/v1/registration_status/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.json()["waitlist_signup_provider"], "internal")


class RegistrationKillSwitchTest(APITestCase):
    def setUp(self):
        cache.clear()
        GameSettings.objects.all().delete()
        self.settings = GameSettings.current()
        InviteCode.objects.create(code="TESTCODE")
        mail.outbox.clear()

    def tearDown(self):
        cache.clear()

    def _post_registration(self):
        with patch("api.serializers._verify_turnstile", return_value=True):
            return self.client.post(
                "/api/v1/auth/registration/",
                {
                    "email": "newuser@example.com",
                    "password1": "SuperSecret123!",
                    "password2": "SuperSecret123!",
                    "invite_code": "TESTCODE",
                    "agree_to_terms": True,
                    "turnstile_token": "test-token",
                },
            )

    def test_signup_blocked_when_registration_disabled(self):
        self.settings.registration_enabled = False
        self.settings.save()

        res = self._post_registration()

        self.assertEqual(res.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertFalse(User.objects.filter(email="newuser@example.com").exists())
        self.assertFalse(any(m.to == ["newuser@example.com"] for m in mail.outbox))

    def test_signup_blocked_even_with_valid_invite_token(self):
        from users.models import Waitlist as WaitlistModel

        entry = WaitlistModel.objects.create(
            email="invitee@example.com",
            status=WaitlistModel.Status.INVITED,
            invite_token="invite-tok",
        )
        self.settings.registration_enabled = False
        self.settings.save()

        with patch("api.serializers._verify_turnstile", return_value=True):
            res = self.client.post(
                "/api/v1/auth/registration/",
                {
                    "email": entry.email,
                    "password1": "SuperSecret123!",
                    "password2": "SuperSecret123!",
                    "invite_token": entry.invite_token,
                    "agree_to_terms": True,
                    "turnstile_token": "test-token",
                },
            )

        self.assertEqual(res.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertFalse(User.objects.filter(email=entry.email).exists())

    def test_signup_succeeds_when_registration_enabled(self):
        self.settings.registration_enabled = True
        self.settings.save()

        res = self._post_registration()

        self.assertIn(res.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
        self.assertTrue(User.objects.filter(email="newuser@example.com").exists())


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class WaitlistJoinAPITest(APITestCase):
    def setUp(self):
        cache.clear()
        mail.outbox.clear()

    def tearDown(self):
        cache.clear()

    def test_valid_email_creates_waiting_entry(self):
        res = self.client.post(
            "/api/v1/waitlist_join/", {"email": "waiter@example.com"}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        entry = Waitlist.objects.get(email="waiter@example.com")
        self.assertEqual(entry.status, Waitlist.Status.WAITING)

    def test_valid_email_sends_confirmation_email(self):
        with self.captureOnCommitCallbacks(execute=True):
            res = self.client.post(
                "/api/v1/waitlist_join/", {"email": "waiter@example.com"}
            )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["waiter@example.com"])
        self.assertIn("waitlist", mail.outbox[0].subject.lower())

    def test_duplicate_email_while_waiting_does_not_create_second_row(self):
        Waitlist.objects.create(email="waiter@example.com")
        res = self.client.post(
            "/api/v1/waitlist_join/", {"email": "waiter@example.com"}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(Waitlist.objects.filter(email="waiter@example.com").count(), 1)

    def test_duplicate_email_while_waiting_does_not_resend_confirmation(self):
        Waitlist.objects.create(email="waiter@example.com")
        with self.captureOnCommitCallbacks(execute=True):
            res = self.client.post(
                "/api/v1/waitlist_join/", {"email": "waiter@example.com"}
            )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)

    def test_email_normalized_to_lowercase(self):
        res = self.client.post(
            "/api/v1/waitlist_join/", {"email": "Waiter@Example.com"}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(Waitlist.objects.filter(email="waiter@example.com").exists())

    def test_rate_limit_triggers_on_eleventh_request(self):
        for i in range(10):
            res = self.client.post(
                "/api/v1/waitlist_join/", {"email": f"waiter{i}@example.com"}
            )
            self.assertEqual(res.status_code, status.HTTP_200_OK)
        res = self.client.post(
            "/api/v1/waitlist_join/", {"email": "waiter11@example.com"}
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class SignupIgnoresCapTest(APITestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_signup_succeeds_even_when_cap_already_exceeded(self):
        from users.models import InviteCode

        GameSettings.objects.all().delete()
        settings_obj = GameSettings.current()
        User.objects.create_user(
            email="existing@example.com", password="testpassword123"
        )
        settings_obj.registration_cap = 0
        settings_obj.save()
        InviteCode.objects.create(code="TESTCODE")

        with patch("api.serializers._verify_turnstile", return_value=True):
            res = self.client.post(
                "/api/v1/auth/registration/",
                {
                    "email": "newuser@example.com",
                    "password1": "SuperSecret123!",
                    "password2": "SuperSecret123!",
                    "invite_code": "TESTCODE",
                    "agree_to_terms": True,
                    "turnstile_token": "test-token",
                },
            )
        self.assertIn(res.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
        self.assertTrue(User.objects.filter(email="newuser@example.com").exists())


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class WaitlistServiceEmailTest(TestCase):
    def setUp(self):
        self.entry = Waitlist.objects.create(email="waiter@example.com")

    def test_send_signup_confirmation_email_sends_to_entry_email(self):
        with self.captureOnCommitCallbacks(execute=True):
            waitlist_service.send_signup_confirmation_email(self.entry)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["waiter@example.com"])

    def test_invite_entry_sends_email_and_sets_fields(self):
        with self.captureOnCommitCallbacks(execute=True):
            waitlist_service.invite_entry(self.entry)

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.status, Waitlist.Status.INVITED)
        self.assertIsNotNone(self.entry.invite_token)
        self.assertIsNotNone(self.entry.invited_at)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["waiter@example.com"])
        self.assertIn(self.entry.invite_token, mail.outbox[0].body)

    def test_invite_entry_preserves_existing_token(self):
        self.entry.invite_token = "existing-token"
        self.entry.status = Waitlist.Status.INVITED
        self.entry.save()

        with self.captureOnCommitCallbacks(execute=True):
            waitlist_service.invite_entry(self.entry)

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.invite_token, "existing-token")
        self.assertEqual(len(mail.outbox), 1)

    def test_resend_invite_email_does_not_change_token_or_timestamp(self):
        with self.captureOnCommitCallbacks(execute=True):
            waitlist_service.invite_entry(self.entry)
        mail.outbox.clear()
        original_token = self.entry.invite_token
        original_invited_at = self.entry.invited_at

        with self.captureOnCommitCallbacks(execute=True):
            waitlist_service.resend_invite_email(self.entry)

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.invite_token, original_token)
        self.assertEqual(self.entry.invited_at, original_invited_at)
        self.assertEqual(len(mail.outbox), 1)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class WaitlistAdminActionsTest(TestCase):
    def setUp(self):
        from django.contrib.admin.sites import AdminSite
        from django.contrib.messages.storage.fallback import FallbackStorage
        from django.test import RequestFactory
        from users.admin import WaitlistAdmin

        self.admin = WaitlistAdmin(Waitlist, AdminSite())
        request = RequestFactory().post("/admin/")
        request.session = {}
        request._messages = FallbackStorage(request)
        self.factory_request = request

    def test_invite_selected_now_only_affects_waiting_entries(self):
        waiting1 = Waitlist.objects.create(email="w1@example.com")
        waiting2 = Waitlist.objects.create(email="w2@example.com")
        already_invited = Waitlist.objects.create(
            email="i1@example.com", status=Waitlist.Status.INVITED
        )

        with self.captureOnCommitCallbacks(execute=True):
            self.admin.invite_selected_now(
                self.factory_request,
                Waitlist.objects.filter(
                    pk__in=[waiting1.pk, waiting2.pk, already_invited.pk]
                ),
            )

        waiting1.refresh_from_db()
        waiting2.refresh_from_db()
        already_invited.refresh_from_db()
        self.assertEqual(waiting1.status, Waitlist.Status.INVITED)
        self.assertEqual(waiting2.status, Waitlist.Status.INVITED)
        self.assertEqual(already_invited.status, Waitlist.Status.INVITED)
        self.assertEqual(len(mail.outbox), 2)

    def test_resend_invite_email_action_only_affects_invited_entries(self):
        invited = Waitlist.objects.create(
            email="i1@example.com",
            status=Waitlist.Status.INVITED,
            invite_token="tok",
        )
        waiting = Waitlist.objects.create(email="w1@example.com")

        with self.captureOnCommitCallbacks(execute=True):
            self.admin.resend_invite_email_action(
                self.factory_request,
                Waitlist.objects.filter(pk__in=[invited.pk, waiting.pk]),
            )

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["i1@example.com"])

    def test_mark_as_removed_sets_status_regardless_of_prior_status(self):
        entry = Waitlist.objects.create(email="w1@example.com")
        self.admin.mark_as_removed(
            self.factory_request, Waitlist.objects.filter(pk=entry.pk)
        )
        entry.refresh_from_db()
        self.assertEqual(entry.status, Waitlist.Status.REMOVED)

    def test_export_selected_to_csv(self):
        entry = Waitlist.objects.create(email="w1@example.com")
        response = self.admin.export_selected_to_csv(
            self.factory_request, Waitlist.objects.filter(pk=entry.pk)
        )
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn(b"w1@example.com", response.content)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class WaitlistInviteTaskTest(TestCase):
    def setUp(self):
        GameSettings.objects.all().delete()
        self.settings = GameSettings.current()

    def _create_waiting(self, n, prefix="w"):
        return [
            Waitlist.objects.create(email=f"{prefix}{i}@example.com") for i in range(n)
        ]

    def test_headroom_greater_than_queue_invites_everyone(self):
        entries = self._create_waiting(3)
        self.settings.registration_cap = 100
        self.settings.save()

        count = waitlist_service.invite_up_to_headroom()

        self.assertEqual(count, 3)
        for entry in entries:
            entry.refresh_from_db()
            self.assertEqual(entry.status, Waitlist.Status.INVITED)

    def test_headroom_less_than_queue_invites_oldest_n(self):
        entries = self._create_waiting(5)
        self.settings.registration_cap = User.objects.count() + 2
        self.settings.save()

        count = waitlist_service.invite_up_to_headroom()

        self.assertEqual(count, 2)
        invited = [
            e
            for e in entries
            if Waitlist.objects.get(pk=e.pk).status == Waitlist.Status.INVITED
        ]
        self.assertEqual({e.pk for e in invited}, {entries[0].pk, entries[1].pk})

    def test_headroom_zero_or_negative_invites_nobody(self):
        self._create_waiting(2)
        self.settings.registration_cap = 0
        self.settings.save()

        count = waitlist_service.invite_up_to_headroom()

        self.assertEqual(count, 0)
        self.assertFalse(
            Waitlist.objects.filter(status=Waitlist.Status.INVITED).exists()
        )

    def test_non_waiting_entries_are_never_touched(self):
        invited = Waitlist.objects.create(
            email="already-invited@example.com",
            status=Waitlist.Status.INVITED,
            invite_token="tok",
        )
        redeemed = Waitlist.objects.create(
            email="redeemed@example.com", status=Waitlist.Status.REDEEMED
        )
        removed = Waitlist.objects.create(
            email="removed@example.com", status=Waitlist.Status.REMOVED
        )
        self.settings.registration_cap = 100
        self.settings.save()

        waitlist_service.invite_up_to_headroom()

        invited.refresh_from_db()
        redeemed.refresh_from_db()
        removed.refresh_from_db()
        self.assertEqual(invited.invite_token, "tok")
        self.assertEqual(redeemed.status, Waitlist.Status.REDEEMED)
        self.assertEqual(removed.status, Waitlist.Status.REMOVED)

    def test_calling_twice_back_to_back_second_run_invites_zero(self):
        self._create_waiting(2)
        self.settings.registration_cap = User.objects.count() + 2
        self.settings.save()

        first = waitlist_service.invite_up_to_headroom()
        second = waitlist_service.invite_up_to_headroom()

        self.assertEqual(first, 2)
        self.assertEqual(second, 0)


class WaitlistRegistrationRedemptionTest(APITestCase):
    def setUp(self):
        cache.clear()
        GameSettings.objects.all().delete()
        GameSettings.current()

    def tearDown(self):
        cache.clear()

    def _register_payload(self, email, invite_token):
        return {
            "email": email,
            "password1": "SuperSecret123!",
            "password2": "SuperSecret123!",
            "invite_token": invite_token,
            "agree_to_terms": True,
            "turnstile_token": "test-token",
        }

    def _post_register(self, payload):
        with patch("api.serializers._verify_turnstile", return_value=True):
            return self.client.post("/api/v1/auth/registration/", payload)

    def test_valid_token_and_matching_email_succeeds_and_redeems(self):
        entry = Waitlist.objects.create(
            email="invitee@example.com",
            status=Waitlist.Status.INVITED,
            invite_token="tok-valid",
        )
        res = self._post_register(
            self._register_payload("invitee@example.com", "tok-valid")
        )
        self.assertIn(res.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
        self.assertTrue(User.objects.filter(email="invitee@example.com").exists())
        entry.refresh_from_db()
        self.assertEqual(entry.status, Waitlist.Status.REDEEMED)

    def test_valid_token_mismatched_email_rejected(self):
        entry = Waitlist.objects.create(
            email="invitee@example.com",
            status=Waitlist.Status.INVITED,
            invite_token="tok-mismatch",
        )
        res = self._post_register(
            self._register_payload("someone-else@example.com", "tok-mismatch")
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        entry.refresh_from_db()
        self.assertEqual(entry.status, Waitlist.Status.INVITED)
        self.assertFalse(User.objects.filter(email="someone-else@example.com").exists())

    def test_already_redeemed_token_rejected(self):
        Waitlist.objects.create(
            email="invitee@example.com",
            status=Waitlist.Status.REDEEMED,
            invite_token="tok-used",
        )
        res = self._post_register(
            self._register_payload("invitee@example.com", "tok-used")
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email="invitee@example.com").exists())

    def test_both_invite_code_and_invite_token_rejected(self):
        Waitlist.objects.create(
            email="invitee@example.com",
            status=Waitlist.Status.INVITED,
            invite_token="tok-both",
        )
        InviteCode.objects.create(code="SOMECODE")
        payload = self._register_payload("invitee@example.com", "tok-both")
        payload["invite_code"] = "SOMECODE"
        res = self._post_register(payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email="invitee@example.com").exists())

    def test_neither_invite_code_nor_invite_token_rejected(self):
        payload = self._register_payload("invitee@example.com", "")
        del payload["invite_token"]
        res = self._post_register(payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email="invitee@example.com").exists())

    def test_concurrent_redemption_race_leaves_no_orphaned_user(self):
        Waitlist.objects.create(
            email="invitee@example.com",
            status=Waitlist.Status.INVITED,
            invite_token="tok-race",
        )

        # Simulate another request winning the race: the conditional UPDATE
        # in custom_signup() matches zero rows, as if a concurrent request
        # already flipped this entry to REDEEMED first.
        mock_queryset = MagicMock()
        mock_queryset.update.return_value = 0
        with patch(
            "api.serializers.Waitlist.objects.filter", return_value=mock_queryset
        ):
            res = self._post_register(
                self._register_payload("invitee@example.com", "tok-race")
            )

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email="invitee@example.com").exists())


class WaitlistModelConstraintTest(TestCase):
    def test_duplicate_active_email_raises_integrity_error(self):
        Waitlist.objects.create(email="dup@example.com", status=Waitlist.Status.WAITING)
        with self.assertRaises(IntegrityError):
            Waitlist.objects.create(
                email="dup@example.com", status=Waitlist.Status.INVITED
            )

    def test_removed_entry_does_not_block_new_waiting_entry(self):
        Waitlist.objects.create(email="dup@example.com", status=Waitlist.Status.REMOVED)
        Waitlist.objects.create(email="dup@example.com", status=Waitlist.Status.WAITING)
        self.assertEqual(Waitlist.objects.filter(email="dup@example.com").count(), 2)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class WaitlistNudgeTest(TestCase):
    def setUp(self):
        GameSettings.objects.all().delete()
        self.settings = GameSettings.current()
        self.settings.waitlist_nudges_enabled_from = timezone.now() - timedelta(
            days=365
        )
        self.settings.save()

    def _create_invited(self, email, days_ago, **extra):
        return Waitlist.objects.create(
            email=email,
            status=Waitlist.Status.INVITED,
            invite_token=f"tok-{email}",
            invited_at=timezone.now() - timedelta(days=days_ago),
            **extra,
        )

    def test_sends_3day_nudge_and_marks_sent(self):
        entry = self._create_invited("three@example.com", 3)

        with self.captureOnCommitCallbacks(execute=True):
            count = waitlist_service.send_due_nudges()

        entry.refresh_from_db()
        self.assertEqual(count, 1)
        self.assertIsNotNone(entry.nudge_3day_sent_at)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["three@example.com"])

    def test_sends_7day_nudge_independently(self):
        # Simulate the 3-day milestone already having been handled by an
        # earlier scan, so this run only newly crosses the 7-day mark.
        entry = self._create_invited(
            "seven@example.com", 7, nudge_3day_sent_at=timezone.now()
        )

        with self.captureOnCommitCallbacks(execute=True):
            waitlist_service.send_due_nudges()

        entry.refresh_from_db()
        self.assertIsNotNone(entry.nudge_7day_sent_at)

    def test_sends_30day_nudge_independently(self):
        # Simulate the 3/7-day milestones already having been handled by
        # earlier scans, so this run only newly crosses the 30-day mark.
        entry = self._create_invited(
            "thirty@example.com",
            30,
            nudge_3day_sent_at=timezone.now(),
            nudge_7day_sent_at=timezone.now(),
        )

        with self.captureOnCommitCallbacks(execute=True):
            waitlist_service.send_due_nudges()

        entry.refresh_from_db()
        self.assertIsNotNone(entry.nudge_30day_sent_at)

    def test_no_send_before_next_milestone(self):
        entry = self._create_invited("early@example.com", 1)

        with self.captureOnCommitCallbacks(execute=True):
            count = waitlist_service.send_due_nudges()

        entry.refresh_from_db()
        self.assertEqual(count, 0)
        self.assertIsNone(entry.nudge_3day_sent_at)
        self.assertEqual(len(mail.outbox), 0)

    def test_does_not_resend_milestone_already_sent(self):
        entry = self._create_invited(
            "already@example.com", 3, nudge_3day_sent_at=timezone.now()
        )

        with self.captureOnCommitCallbacks(execute=True):
            count = waitlist_service.send_due_nudges()

        self.assertEqual(count, 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_skips_redeemed_and_removed_entries(self):
        redeemed = self._create_invited("redeemed@example.com", 10)
        redeemed.status = Waitlist.Status.REDEEMED
        redeemed.save()
        removed = self._create_invited("removed@example.com", 10)
        removed.status = Waitlist.Status.REMOVED
        removed.save()

        with self.captureOnCommitCallbacks(execute=True):
            count = waitlist_service.send_due_nudges()

        self.assertEqual(count, 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_terminal_milestone_sends_removal_email_and_flips_status(self):
        # Simulate the earlier milestones already having been handled by
        # earlier scans, so this run only newly crosses the 60-day mark.
        entry = self._create_invited(
            "stale@example.com",
            60,
            nudge_3day_sent_at=timezone.now(),
            nudge_7day_sent_at=timezone.now(),
            nudge_30day_sent_at=timezone.now(),
        )

        with self.captureOnCommitCallbacks(execute=True):
            count = waitlist_service.send_due_nudges()

        entry.refresh_from_db()
        self.assertEqual(count, 1)
        self.assertIsNotNone(entry.nudge_removal_sent_at)
        self.assertEqual(entry.status, Waitlist.Status.REMOVED)
        self.assertEqual(len(mail.outbox), 1)

    def test_terminal_race_with_redemption_leaves_entry_redeemed(self):
        entry = self._create_invited("racer@example.com", 60)
        # Simulate a redemption winning the race between the scan's read
        # and its guarded update.
        Waitlist.objects.filter(pk=entry.pk).update(status=Waitlist.Status.REDEEMED)

        waitlist_service.send_due_nudges()

        entry.refresh_from_db()
        self.assertEqual(entry.status, Waitlist.Status.REDEEMED)
        self.assertIsNone(entry.nudge_removal_sent_at)

    def test_entries_before_cutoff_are_excluded(self):
        entry = self._create_invited("old@example.com", 60)
        self.settings.waitlist_nudges_enabled_from = timezone.now()
        self.settings.save()

        with self.captureOnCommitCallbacks(execute=True):
            count = waitlist_service.send_due_nudges()

        entry.refresh_from_db()
        self.assertEqual(count, 0)
        self.assertEqual(entry.status, Waitlist.Status.INVITED)
        self.assertIsNone(entry.nudge_removal_sent_at)

    def test_no_cutoff_set_sends_nothing(self):
        self.settings.waitlist_nudges_enabled_from = None
        self.settings.save()
        self._create_invited("uncut@example.com", 60)

        count = waitlist_service.send_due_nudges()

        self.assertEqual(count, 0)

    def test_send_waitlist_nudges_task_delegates_and_returns_count(self):
        from users.tasks import send_waitlist_nudges

        self._create_invited("task@example.com", 3)

        with self.captureOnCommitCallbacks(execute=True):
            result = send_waitlist_nudges.delay()

        self.assertEqual(result.get(), 1)
        self.assertEqual(len(mail.outbox), 1)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class WaitlistRemovalAcceptanceCriteriaTest(TestCase):
    """
    Regression coverage for #500's stated acceptance criteria, which are
    already satisfied by existing code with no changes: a REMOVED entry
    is excluded from invite headroom, and its email can be reused.
    """

    def setUp(self):
        GameSettings.objects.all().delete()
        self.settings = GameSettings.current()

    def test_removed_entry_excluded_from_invite_headroom(self):
        Waitlist.objects.create(
            email="removed@example.com", status=Waitlist.Status.REMOVED
        )
        self.settings.registration_cap = 100
        self.settings.save()

        count = waitlist_service.invite_up_to_headroom()

        self.assertEqual(count, 0)

    def test_removed_entrys_email_can_rejoin_waitlist(self):
        Waitlist.objects.create(
            email="removed@example.com", status=Waitlist.Status.REMOVED
        )
        res = self.client.post(
            "/api/v1/waitlist_join/", {"email": "removed@example.com"}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(
            Waitlist.objects.filter(
                email="removed@example.com", status=Waitlist.Status.WAITING
            ).exists()
        )

    def test_removed_entrys_old_invite_token_cannot_be_redeemed(self):
        from api.serializers import CustomRegisterSerializer

        Waitlist.objects.create(
            email="removed@example.com",
            status=Waitlist.Status.REMOVED,
            invite_token="tok-removed",
        )
        username_field = CustomRegisterSerializer._declared_fields["username"]
        with patch("api.serializers._verify_turnstile", return_value=True):
            with patch.dict(username_field._kwargs, {"required": False}):
                res = self.client.post(
                    "/api/v1/auth/registration/",
                    {
                        "email": "removed@example.com",
                        "password1": "SuperSecret123!",
                        "password2": "SuperSecret123!",
                        "invite_token": "tok-removed",
                        "agree_to_terms": True,
                        "turnstile_token": "test-token",
                    },
                )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email="removed@example.com").exists())


class SelfServeRegistrationTest(APITestCase):
    def setUp(self):
        cache.clear()
        GameSettings.objects.all().delete()
        self.settings = GameSettings.current()

    def tearDown(self):
        cache.clear()

    def _register_payload(self, email, **extra):
        return {
            "email": email,
            "password1": "SuperSecret123!",
            "password2": "SuperSecret123!",
            "agree_to_terms": True,
            "turnstile_token": "test-token",
            **extra,
        }

    def _post_register(self, payload):
        with patch("api.serializers._verify_turnstile", return_value=True):
            return self.client.post("/api/v1/auth/registration/", payload)

    def _enable_self_serve(self):
        self.settings.self_serve_registration = True
        self.settings.save()

    def test_no_invite_rejected_when_self_serve_disabled(self):
        res = self._post_register(self._register_payload("solo@example.com"))
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email="solo@example.com").exists())

    def test_no_invite_succeeds_when_self_serve_enabled(self):
        self._enable_self_serve()
        res = self._post_register(self._register_payload("solo@example.com"))
        self.assertIn(res.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
        self.assertTrue(User.objects.filter(email="solo@example.com").exists())

    def test_blank_invite_code_treated_as_self_serve(self):
        self._enable_self_serve()
        res = self._post_register(
            self._register_payload("solo@example.com", invite_code="")
        )
        self.assertIn(res.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
        self.assertTrue(User.objects.filter(email="solo@example.com").exists())

    def test_self_serve_respects_registration_cap(self):
        self._enable_self_serve()
        existing = User.objects.create_user(
            email="a@example.com", password="testpassword123"
        )
        existing.is_confirmed = True
        existing.save(update_fields=["is_confirmed"])
        self.settings.registration_cap = User.objects.count()
        self.settings.save()
        res = self._post_register(self._register_payload("solo@example.com"))
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email="solo@example.com").exists())

    def test_self_serve_ignores_unconfirmed_users_for_cap(self):
        self._enable_self_serve()
        User.objects.create_user(email="a@example.com", password="testpassword123")
        self.settings.registration_cap = User.objects.count()
        self.settings.save()
        res = self._post_register(self._register_payload("solo@example.com"))
        self.assertIn(res.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
        self.assertTrue(User.objects.filter(email="solo@example.com").exists())

    def test_invite_token_still_bypasses_cap_when_self_serve_enabled(self):
        self._enable_self_serve()
        User.objects.create_user(email="a@example.com", password="testpassword123")
        self.settings.registration_cap = User.objects.count()
        self.settings.save()
        Waitlist.objects.create(
            email="invitee@example.com",
            status=Waitlist.Status.INVITED,
            invite_token="tok-selfserve",
        )
        res = self._post_register(
            self._register_payload("invitee@example.com", invite_token="tok-selfserve")
        )
        self.assertIn(res.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
        self.assertTrue(User.objects.filter(email="invitee@example.com").exists())

    def test_invite_code_still_works_when_self_serve_enabled(self):
        self._enable_self_serve()
        invite = InviteCode.objects.create(code="SELFSERVE")
        res = self._post_register(
            self._register_payload("coded@example.com", invite_code="SELFSERVE")
        )
        self.assertIn(res.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
        self.assertTrue(User.objects.filter(email="coded@example.com").exists())
        invite.refresh_from_db()
        self.assertEqual(invite.uses, 1)

    def test_both_invite_code_and_token_still_rejected(self):
        self._enable_self_serve()
        InviteCode.objects.create(code="SOMECODE")
        Waitlist.objects.create(
            email="invitee@example.com",
            status=Waitlist.Status.INVITED,
            invite_token="tok-both-ss",
        )
        res = self._post_register(
            self._register_payload(
                "invitee@example.com",
                invite_code="SOMECODE",
                invite_token="tok-both-ss",
            )
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email="invitee@example.com").exists())

    def test_kill_switch_blocks_self_serve_signups(self):
        self._enable_self_serve()
        self.settings.registration_enabled = False
        self.settings.save()
        res = self._post_register(self._register_payload("solo@example.com"))
        self.assertEqual(res.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertFalse(User.objects.filter(email="solo@example.com").exists())


class RegistrationRateLimitTest(APITestCase):
    def setUp(self):
        cache.clear()
        GameSettings.objects.all().delete()
        GameSettings.current()
        InviteCode.objects.create(code="RATELIMITCODE")

    def tearDown(self):
        cache.clear()

    def _register_payload(self, email):
        return {
            "email": email,
            "password1": "SuperSecret123!",
            "password2": "SuperSecret123!",
            "invite_code": "RATELIMITCODE",
            "agree_to_terms": True,
            "turnstile_token": "test-token",
        }

    def test_sixth_registration_from_same_ip_is_rate_limited(self):
        with patch("api.serializers._verify_turnstile", return_value=True):
            for i in range(5):
                res = self.client.post(
                    "/api/v1/auth/registration/",
                    self._register_payload(f"rl{i}@example.com"),
                )
                self.assertIn(
                    res.status_code,
                    [status.HTTP_200_OK, status.HTTP_201_CREATED],
                )

            res = self.client.post(
                "/api/v1/auth/registration/",
                self._register_payload("rl5@example.com"),
            )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(User.objects.filter(email="rl5@example.com").exists())


class DisposableEmailBlocklistTest(APITestCase):
    DISPOSABLE_EMAIL = "someone@mailinator.com"

    def setUp(self):
        cache.clear()
        GameSettings.objects.all().delete()
        self.settings = GameSettings.current()
        self.settings.self_serve_registration = True
        self.settings.save()

    def tearDown(self):
        cache.clear()

    def test_registration_rejects_disposable_domain(self):
        with patch("api.serializers._verify_turnstile", return_value=True):
            res = self.client.post(
                "/api/v1/auth/registration/",
                {
                    "email": self.DISPOSABLE_EMAIL,
                    "password1": "SuperSecret123!",
                    "password2": "SuperSecret123!",
                    "agree_to_terms": True,
                    "turnstile_token": "test-token",
                },
            )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email=self.DISPOSABLE_EMAIL).exists())

    def test_registration_accepts_normal_domain(self):
        with patch("api.serializers._verify_turnstile", return_value=True):
            res = self.client.post(
                "/api/v1/auth/registration/",
                {
                    "email": "someone@example.com",
                    "password1": "SuperSecret123!",
                    "password2": "SuperSecret123!",
                    "agree_to_terms": True,
                    "turnstile_token": "test-token",
                },
            )
        self.assertIn(res.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])

    def test_waitlist_signup_rejects_disposable_domain(self):
        with patch("api.views.subscribe_email_to_waitlist") as mock_subscribe:
            res = self.client.post(
                "/api/v1/waitlist_signup/", {"email": self.DISPOSABLE_EMAIL}
            )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        mock_subscribe.assert_not_called()

    def test_waitlist_join_rejects_disposable_domain(self):
        res = self.client.post(
            "/api/v1/waitlist_join/", {"email": self.DISPOSABLE_EMAIL}
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Waitlist.objects.filter(email=self.DISPOSABLE_EMAIL).exists())


class AdminAutoConfirmGatingTest(TestCase):
    def setUp(self):
        from django.contrib.admin.sites import AdminSite
        from django.contrib.messages.storage.fallback import FallbackStorage
        from django.test import RequestFactory
        from users.admin import CustomUserAdmin

        GameSettings.objects.all().delete()
        self.settings = GameSettings.current()
        self.admin = CustomUserAdmin(User, AdminSite())
        request = RequestFactory().post("/admin/")
        request.session = {}
        request._messages = FallbackStorage(request)
        self.request = request

    def _save_new_user(self, email):
        user = User(email=email)
        user.set_password("testpassword123")
        form = MagicMock()
        self.admin.save_model(self.request, user, form, change=False)
        return user

    def test_concierge_mode_auto_confirms_new_admin_user(self):
        self.settings.self_serve_registration = False
        self.settings.save()
        user = self._save_new_user("concierge@example.com")
        self.assertTrue(user.is_confirmed)

    def test_self_serve_mode_does_not_auto_confirm_new_admin_user(self):
        self.settings.self_serve_registration = True
        self.settings.save()
        user = self._save_new_user("selfserve@example.com")
        self.assertFalse(user.is_confirmed)
