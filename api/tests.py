import hashlib

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
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

    def test_me_player_patch_updates_name(self):
        self.authenticate()

        res = self.client.patch(
            self.me_player_url, {"name": "  Red Fox  "}, format="json"
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.user.player.refresh_from_db()
        self.assertEqual(self.user.player.name, "Red Fox")
        self.assertEqual(res.data["name"], "Red Fox")

    def test_me_player_patch_rejects_invalid_name(self):
        self.authenticate()
        original_name = self.user.player.name

        res = self.client.patch(
            self.me_player_url, {"name": "bad!!name"}, format="json"
        )

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.player.refresh_from_db()
        self.assertEqual(self.user.player.name, original_name)
        self.assertIn("name", res.data)

    def test_complete_onboarding_sets_flag(self):
        self.authenticate()
        self.user.player.onboarding_completed = False
        self.user.player.save(update_fields=["onboarding_completed"])

        res = self.client.post(self.me_complete_onboarding_url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.user.player.refresh_from_db()
        self.assertTrue(self.user.player.onboarding_completed)
        self.assertEqual(res.data, {"onboarding_completed": True})


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
