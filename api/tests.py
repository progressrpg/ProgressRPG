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
from gameplay.models import Quest
from progression.models import CharacterQuest

User = get_user_model()


class TestMeViewSet(APITestCase):
    def setUp(self):
        self.character = Character.objects.create(name="Hero", can_link=True)
        self.user = User.objects.create_user(
            email="duncan@example.com",
            password="pass12345",
        )

        self.me_url = reverse("me-list")
        self.me_player_url = reverse("me-player")
        self.me_complete_onboarding_url = reverse("me-complete-onboarding")

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


class CustomTokenObtainPairViewTests(APITestCase):
    def setUp(self):
        self.url = reverse("jwt_create")
        self.user = User.objects.create_user(
            email="rememberme@example.com",
            password="pass12345",
        )

    def _refresh_expiry(self, refresh_token):
        exp_timestamp = RefreshToken(refresh_token)["exp"]
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
