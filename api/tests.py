import hashlib
from datetime import datetime, timezone

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from unittest import skip
from unittest.mock import patch, MagicMock

from character.models import Character, PlayerCharacterLink
from core.models import Announcement, PlayerAnnouncementState
from gameplay.models import Quest
from progression.models import CharacterQuest, PlayerActivity
from server_management.models import FeatureFlag
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
        self.character = Character.objects.create(name="Hero", can_link=True)
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

    def test_today_points_null_when_no_active_link(self):
        self.authenticate()
        player = player_for(self.user)
        self.assertIsNone(player.active_link)

        res = self.client.get(reverse("me-today-points"))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIsNone(res.data["points_today"])

    def test_today_points_reflects_todays_completed_activities(self):
        self.authenticate()
        player = player_for(self.user)
        PlayerCharacterLink.objects.create(player=player, character=self.character)

        PlayerActivity.objects.create(
            player=player,
            is_complete=True,
            duration=1200,  # 20 minutes -> 2 points
            completed_at=datetime.now(timezone.utc),
        )

        res = self.client.get(reverse("me-today-points"))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["points_today"], 2)


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


class PlayerActivityGroupKeyAPITests(APITestCase):
    def setUp(self):
        self.user = create_test_user(
            email="activity-groups@example.com",
            password="pass12345",
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse("playeractivity-list")

    def test_create_reuses_dominant_exact_match_group_key(self):
        PlayerActivity.objects.create(
            player=player_for(self.user),
            name="Morning planning",
            group_key="morning-planning",
        )
        PlayerActivity.objects.create(
            player=player_for(self.user),
            name="morning planning",
            group_key="morning-planning",
        )

        response = self.client.post(
            self.url,
            {"name": "MORNING PLANNING", "duration": 300},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["activity"]["group_key"],
            "morning-planning",
        )
