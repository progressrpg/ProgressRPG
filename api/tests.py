from datetime import time
import hashlib
from datetime import datetime, timezone

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone as dj_timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from unittest import skip
from unittest.mock import patch, MagicMock

from character.models import Character, PlayerCharacterLink
from core.models import Announcement, FeatureFlag, GameSettings, PlayerAnnouncementState
from progression.models import Activity, PlayerActivity
from users.models import CustomUserManager, Player

User = get_user_model()


def create_test_user(*, email: str, password: str):
    manager = User.objects
    assert isinstance(manager, CustomUserManager)
    return manager.create_user(email=email, password=password)


def player_for(user) -> Player:
    player = getattr(user, "player", None)
    assert isinstance(player, Player)
    return player


class TestMeViewSet(APITestCase):
    def setUp(self):
        self.character = Character.objects.create(given_name="Hero")
        self.user = create_test_user(
            email="duncan@example.com",
            password="pass12345",
        )

        self.me_url = reverse("me-list")
        self.me_player_url = reverse("me-player")
        self.me_complete_onboarding_url = reverse("me-complete-onboarding")
        self.fetch_info_url = reverse("fetch_info")

    def authenticate(self):
        self.client.force_authenticate(user=self.user)

    def test_me_list_requires_auth(self):
        res = self.client.get(self.me_url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_list_returns_current_user(self):
        self.authenticate()

        res = self.client.get(self.me_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["email"], self.user.email)

    def test_me_player_returns_achievements(self):
        self.authenticate()

        res = self.client.get(self.me_player_url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("achievements", res.data)
        self.assertEqual(len(res.data["achievements"]), 3)

    def test_fetch_info_returns_player_achievements(self):
        self.authenticate()

        res = self.client.get(self.fetch_info_url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("achievements", res.data["player"])
        self.assertEqual(len(res.data["player"]["achievements"]), 3)

    def test_fetch_info_includes_announcement_unread_count(self):
        self.authenticate()
        Announcement.objects.create(
            title="Server update",
            summary="Small update",
            body="We shipped a fix.",
            is_published=True,
        )

        res = self.client.get(self.fetch_info_url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["announcement_unread_count"], 1)

    def test_me_announcements_marks_read_per_player(self):
        self.authenticate()
        announcement = Announcement.objects.create(
            title="Patch notes",
            summary="v1",
            body="Changes.",
            is_published=True,
        )

        res_list = self.client.get(reverse("me-announcements"))
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        self.assertEqual(res_list.data["unread_count"], 1)
        self.assertEqual(len(res_list.data["results"]), 1)
        self.assertFalse(res_list.data["results"][0]["is_read"])

        res_read = self.client.post(
            reverse("me-mark-announcement-read"),
            {"announcement_id": announcement.pk},
            format="json",
        )
        self.assertEqual(res_read.status_code, status.HTTP_200_OK)
        self.assertEqual(res_read.data["unread_count"], 0)

        player_for(self.user).refresh_from_db()
        self.assertTrue(
            PlayerAnnouncementState.objects.filter(
                player=player_for(self.user),
                announcement=announcement,
                read_at__isnull=False,
            ).exists()
        )

    def test_me_mark_all_announcements_read(self):
        self.authenticate()
        Announcement.objects.create(
            title="One",
            summary="",
            body="A",
            is_published=True,
        )
        Announcement.objects.create(
            title="Two",
            summary="",
            body="B",
            is_published=True,
        )

        res_mark_all = self.client.post(reverse("me-mark-all-announcements-read"))
        self.assertEqual(res_mark_all.status_code, status.HTTP_200_OK)
        self.assertEqual(res_mark_all.data["unread_count"], 0)

        res_count = self.client.get(reverse("me-announcements-unread-count"))
        self.assertEqual(res_count.status_code, status.HTTP_200_OK)
        self.assertEqual(res_count.data["unread_count"], 0)

    def test_me_player_patch_updates_name(self):
        self.authenticate()

        res = self.client.patch(
            self.me_player_url, {"name": "  Red Fox  "}, format="json"
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        player_for(self.user).refresh_from_db()
        self.assertEqual(player_for(self.user).name, "Red Fox")
        self.assertEqual(res.data["name"], "Red Fox")

    def test_me_player_patch_rejects_invalid_name(self):
        self.authenticate()
        original_name = player_for(self.user).name

        res = self.client.patch(
            self.me_player_url, {"name": "bad!!name"}, format="json"
        )

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        player_for(self.user).refresh_from_db()
        self.assertEqual(player_for(self.user).name, original_name)
        self.assertIn("name", res.data)

    def test_me_player_patch_rejects_profane_name(self):
        self.authenticate()
        original_name = player_for(self.user).name

        res = self.client.patch(
            self.me_player_url, {"name": "b1tch-mage"}, format="json"
        )

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        player_for(self.user).refresh_from_db()
        self.assertEqual(player_for(self.user).name, original_name)
        self.assertIn("name", res.data)

    def test_complete_onboarding_sets_flag(self):
        self.authenticate()
        player_for(self.user).onboarding_completed = False
        player_for(self.user).save(update_fields=["onboarding_completed"])

        res = self.client.post(self.me_complete_onboarding_url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        player_for(self.user).refresh_from_db()
        self.assertTrue(player_for(self.user).onboarding_completed)
        self.assertEqual(res.data, {"onboarding_completed": True})

    def test_daily_goals_null_when_no_active_link(self):
        self.authenticate()
        player = player_for(self.user)
        self.assertIsNone(player.active_link)

        res = self.client.get(reverse("me-daily-goals"))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIsNone(res.data["goals"])

    def test_daily_goals_all_false_when_linked_but_no_activity_or_login(self):
        self.authenticate()
        player = player_for(self.user)
        PlayerCharacterLink.objects.create(player=player, character=self.character)

        res = self.client.get(reverse("me-daily-goals"))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        goals = res.data["goals"]
        self.assertFalse(goals["logged_in_today"])
        self.assertFalse(goals["completed_activity_today"])
        self.assertEqual(goals["activity_minutes_today"], 0)
        self.assertFalse(goals["minutes_goal_met"])
        self.assertFalse(goals["all_goals_met"])
        self.assertFalse(goals["bonus_awarded_today"])
        self.assertEqual(goals["bonus_ap"], 0)

    def test_daily_goals_reflects_todays_completed_activities(self):
        self.authenticate()
        player = player_for(self.user)
        PlayerCharacterLink.objects.create(player=player, character=self.character)

        PlayerActivity.objects.create(
            player=player,
            is_complete=True,
            duration=1200,  # 20 minutes
            completed_at=datetime.now(timezone.utc),
        )

        res = self.client.get(reverse("me-daily-goals"))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        goals = res.data["goals"]
        self.assertTrue(goals["completed_activity_today"])
        self.assertEqual(goals["activity_minutes_today"], 20)
        self.assertTrue(goals["minutes_goal_met"])

    def test_daily_goals_all_met_awards_bonus_once(self):
        from users.models import UserLogin

        self.authenticate()
        player = player_for(self.user)
        PlayerCharacterLink.objects.create(player=player, character=self.character)
        UserLogin.objects.create(user=self.user)

        PlayerActivity.objects.create(
            player=player,
            is_complete=True,
            duration=1200,
            completed_at=datetime.now(timezone.utc),
        )

        res = self.client.get(reverse("me-daily-goals"))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        goals = res.data["goals"]
        self.assertTrue(goals["all_goals_met"])
        # Reads never award the bonus themselves - only activity completion
        # does (via check_and_award_daily_goals), so a plain GET here
        # shouldn't have paid it out.
        self.assertFalse(goals["bonus_awarded_today"])
        self.assertEqual(goals["bonus_ap"], 0)

    def _enable_inactivity_reminders(self):
        # InactivityReminderEmails.is_visible() mirrors this same cutoff
        # (users/dynamic_preferences_registry.py), so the preference is
        # absent from GET/PATCH until it's set - most of these tests need
        # it on to exercise the preference at all.
        settings = GameSettings.current()
        settings.inactivity_reminders_enabled_from = dj_timezone.now()
        settings.save()

    def test_preferences_lists_registered_preferences_with_defaults(self):
        self._enable_inactivity_reminders()
        self.authenticate()

        res = self.client.get(reverse("me-preferences"))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        keys = {item["key"] for item in res.data["preferences"]}
        self.assertIn("notifications__inactivity_reminder_emails", keys)
        item = next(
            i
            for i in res.data["preferences"]
            if i["key"] == "notifications__inactivity_reminder_emails"
        )
        self.assertTrue(item["value"])
        self.assertEqual(item["type"], "boolean")

    def test_preferences_hides_inactivity_reminder_when_feature_disabled(self):
        # GameSettings.inactivity_reminders_enabled_from is unset by
        # default (see setUp / GameSettings.current()'s defaults), so the
        # preference shouldn't appear at all - no point exposing a toggle
        # for a feature that can't do anything yet.
        self.authenticate()

        res = self.client.get(reverse("me-preferences"))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        keys = {item["key"] for item in res.data["preferences"]}
        self.assertNotIn("notifications__inactivity_reminder_emails", keys)

    def test_preferences_patch_rejects_inactivity_reminder_when_feature_disabled(self):
        self.authenticate()

        res = self.client.patch(
            reverse("me-preferences"),
            {"notifications__inactivity_reminder_emails": False},
            format="json",
        )

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_preferences_patch_updates_value(self):
        self._enable_inactivity_reminders()
        self.authenticate()

        res = self.client.patch(
            reverse("me-preferences"),
            {"notifications__inactivity_reminder_emails": False},
            format="json",
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        item = next(
            i
            for i in res.data["preferences"]
            if i["key"] == "notifications__inactivity_reminder_emails"
        )
        self.assertFalse(item["value"])
        self.assertFalse(
            self.user.preferences["notifications__inactivity_reminder_emails"]
        )

    def test_preferences_patch_rejects_unknown_key(self):
        self._enable_inactivity_reminders()
        self.authenticate()

        res = self.client.patch(
            reverse("me-preferences"), {"not_a_real_key": True}, format="json"
        )

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_preferences_patch_rejects_non_boolean_value(self):
        self._enable_inactivity_reminders()
        self.authenticate()

        res = self.client.patch(
            reverse("me-preferences"),
            {"notifications__inactivity_reminder_emails": "not a bool"},
            format="json",
        )

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class CustomTokenObtainPairViewTests(APITestCase):
    def setUp(self):
        self.url = reverse("jwt_create")
        self.user = create_test_user(
            email="rememberme@example.com",
            password="pass12345",
        )

    def _refresh_expiry(self, refresh_token):
        exp_timestamp = float(RefreshToken(refresh_token)["exp"])
        return datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)

    def test_login_uses_short_session_refresh_lifetime_by_default(self):
        response = self.client.post(
            self.url,
            {"email": self.user.email, "password": "pass12345"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.data)
        self.assertIn("refresh_token", response.data)

        short_expiry = self._refresh_expiry(response.data["refresh_token"])
        lifetime = short_expiry - datetime.now(timezone.utc)

        self.assertLess(lifetime.days, 2)

    def test_login_uses_long_session_refresh_lifetime_when_remembered(self):
        short_response = self.client.post(
            self.url,
            {"email": self.user.email, "password": "pass12345"},
            format="json",
        )
        long_response = self.client.post(
            self.url,
            {
                "email": self.user.email,
                "password": "pass12345",
                "remember_me": True,
            },
            format="json",
        )

        self.assertEqual(long_response.status_code, status.HTTP_200_OK)

        short_expiry = self._refresh_expiry(short_response.data["refresh_token"])
        long_expiry = self._refresh_expiry(long_response.data["refresh_token"])

        self.assertGreater(long_expiry, short_expiry)


@override_settings(
    MAILCHIMP_API_KEY="mailchimp-api-key-us13",
    MAILCHIMP_AUDIENCE_ID="audience123",
    MAILCHIMP_SERVER_PREFIX="us13",
)
class WaitlistSignupAPITests(APITestCase):
    def setUp(self):
        self.url = reverse("waitlist_signup")

    @patch("api.mailchimp.http_requests.put")
    def test_waitlist_signup_returns_pending_message(self, mock_put):
        mock_put.return_value = MagicMock(
            ok=True,
            status_code=200,
            json=MagicMock(return_value={"status": "pending"}),
        )

        response = self.client.post(
            self.url,
            {"email": "newperson@example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {
                "detail": "Check your email to confirm your place on the waitlist.",
                "state": "pending",
            },
        )
        subscriber_hash = hashlib.md5(
            "newperson@example.com".encode("utf-8")
        ).hexdigest()
        mock_put.assert_called_once_with(
            f"https://us13.api.mailchimp.com/3.0/lists/audience123/members/{subscriber_hash}",
            auth=("progressrpg", "mailchimp-api-key-us13"),
            json={
                "email_address": "newperson@example.com",
                "status_if_new": "pending",
            },
            timeout=5.0,
        )

    @patch("api.mailchimp.http_requests.put")
    def test_waitlist_signup_returns_success_message(self, mock_put):
        mock_put.return_value = MagicMock(
            ok=True,
            status_code=200,
            json=MagicMock(return_value={"status": "subscribed"}),
        )

        response = self.client.post(
            self.url,
            {"email": "subscribed@example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {
                "detail": "You're on the list! We'll be in touch soon.",
                "state": "subscribed",
            },
        )

    @patch("api.mailchimp.http_requests.put")
    def test_waitlist_signup_returns_invalid_email_message(self, mock_put):
        mock_put.return_value = MagicMock(
            ok=False,
            status_code=400,
            json=MagicMock(
                return_value={
                    "title": "Invalid Resource",
                    "detail": "This email address looks fake or invalid.",
                }
            ),
        )

        response = self.client.post(
            self.url,
            {"email": "person@example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data,
            {"detail": "Please enter a real email address."},
        )

    @override_settings(
        MAILCHIMP_API_KEY="",
        MAILCHIMP_AUDIENCE_ID="",
        MAILCHIMP_SERVER_PREFIX="",
    )
    def test_waitlist_signup_returns_service_unavailable_without_configuration(self):
        response = self.client.post(
            self.url,
            {"email": "person@example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(
            response.data,
            {"detail": "Waitlist signup is temporarily unavailable."},
        )

    def test_waitlist_signup_validates_email(self):
        response = self.client.post(
            self.url,
            {"email": "not-an-email"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)


class AppConfigViewTests(APITestCase):
    def setUp(self):
        self.url = reverse("app_config")

    def test_returns_empty_feature_flags_when_none_configured(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("stripe_live_mode", response.data)
        self.assertEqual(response.data["feature_flags"], {})

    def test_returns_feature_flag_access_groups(self):
        FeatureFlag.objects.create(key="activityList", access_groups=["all"])
        FeatureFlag.objects.create(key="premiumOnlyFeature", access_groups=["premium"])
        FeatureFlag.objects.create(
            key="testersAndPremium", access_groups=["premium", "testers"]
        )
        FeatureFlag.objects.create(key="disabledFeature", access_groups=[])

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["feature_flags"],
            {
                "activityList": ["all"],
                "disabledFeature": [],
                "premiumOnlyFeature": ["premium"],
                "testersAndPremium": ["premium", "testers"],
            },
        )


class PlayerActivityActivityLinkAPITests(APITestCase):
    def setUp(self):
        self.user = create_test_user(
            email="activity-groups@example.com",
            password="pass12345",
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse("playeractivity-list")

    def test_create_reuses_case_insensitive_matching_activity(self):
        existing = PlayerActivity.objects.create(
            player=player_for(self.user),
            name="Morning planning",
        )

        response = self.client.post(
            self.url,
            {"name": "MORNING PLANNING", "duration": 300},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["activity"]["activity"],
            existing.activity_id,
        )
        self.assertEqual(
            Activity.objects.filter(player=player_for(self.user)).count(), 1
        )


class DayStartTimeSettingTests(APITestCase):
    """
    `day_start_time` defines when a player's day rolls over, so it has to be
    editable — a default nobody can change isn't a setting.
    """

    def setUp(self):
        from users.tests import user_factory

        self.user = user_factory(with_player=True)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_day_start_time_can_be_updated(self):
        response = self.client.patch(
            reverse("me-user-settings"), {"day_start_time": "05:30"}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.day_start_time, time(5, 30))

    def test_day_start_time_is_returned_with_the_user(self):
        response = self.client.patch(
            reverse("me-user-settings"), {"day_start_time": "05:30"}, format="json"
        )

        self.assertEqual(response.data["day_start_time"], "05:30:00")

    def test_a_nonsense_time_is_rejected(self):
        response = self.client.patch(
            reverse("me-user-settings"), {"day_start_time": "not a time"}, format="json"
        )

        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertEqual(self.user.day_start_time, time(2, 0))

    def test_timezone_can_be_updated(self):
        response = self.client.patch(
            reverse("me-user-settings"),
            {"timezone": "Europe/London"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(str(self.user.timezone), "Europe/London")

    def test_an_invalid_timezone_is_rejected(self):
        response = self.client.patch(
            reverse("me-user-settings"),
            {"timezone": "Not/A_Timezone"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertEqual(str(self.user.timezone), "UTC")


class TimezoneChoicesTests(APITestCase):
    """
    Backs the Account Preferences tab's timezone picker with every value
    `user_settings`'s `timezone` field will actually accept.
    """

    def setUp(self):
        from users.tests import user_factory

        self.user = user_factory(with_player=True)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_requires_auth(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse("me-timezone-choices"))
        self.assertEqual(response.status_code, 401)

    def test_returns_value_label_pairs_including_known_zones(self):
        response = self.client.get(reverse("me-timezone-choices"))

        self.assertEqual(response.status_code, 200)
        timezones = response.data["timezones"]
        values = {entry["value"] for entry in timezones}
        self.assertIn("Europe/London", values)
        self.assertIn("UTC", values)

        by_value = {entry["value"]: entry["label"] for entry in timezones}
        self.assertEqual(by_value["Europe/London"], "Europe/London")

    def test_every_returned_value_is_accepted_by_user_settings(self):
        response = self.client.get(reverse("me-timezone-choices"))
        sample = response.data["timezones"][0]["value"]

        update = self.client.patch(
            reverse("me-user-settings"), {"timezone": sample}, format="json"
        )

        self.assertEqual(update.status_code, 200)
