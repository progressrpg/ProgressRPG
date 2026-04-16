from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

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
