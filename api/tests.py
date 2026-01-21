from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from unittest import skip

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


class CharacterQuestViewSetTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.character = Character.objects.create(name="Hero", can_link=True)

        cls.user = User.objects.create_user(
            email="testuser@example.com", password="pass1234"
        )
        cls.player = cls.user.player

        cls.quest1 = Quest.objects.create(name="Quest 1", description="Test quest 1")
        cls.quest2 = Quest.objects.create(name="Quest 2", description="Test quest 2")

        cls.char_quest1 = CharacterQuest.objects.create(
            character=cls.character,
            name=cls.quest1.name,
            description=cls.quest1.description,
            target_duration=300,
        )
        cls.char_quest2 = CharacterQuest.objects.create(
            character=cls.character,
            name=cls.quest2.name,
            description=cls.quest2.description,
            target_duration=600,
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # Base URLs
        self.list_url = reverse(
            "characterquest-list"
        )  # DRF router names: <basename>-list
        # self.complete_url1 = reverse(
        #     "characterquest-complete", args=[self.char_quest1.id]
        # )
        # self.complete_url2 = reverse(
        #     "characterquest-complete", args=[self.char_quest2.id]
        # )

    def test_list_character_quests(self):
        """GET /character-quests/ returns CharacterQuest instances for active character"""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", [])
        self.assertEqual(len(results), 2)
        names = [q["name"] for q in results]
        self.assertIn("Quest 1", names)
        self.assertIn("Quest 2", names)

    @skip("No need for character_quest complete method test")
    def test_complete_quest_no_active_character(self):
        """POST returns 400 if user has no active character"""
        PlayerCharacterLink.objects.filter(player=self.player).delete()
        response = self.client.post(self.complete_url1)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_authentication_required_list(self):
        """Unauthenticated user cannot list CharacterQuests"""
        self.client.logout()
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @skip("No need for character_quest complete method test")
    def test_authentication_required_complete(self):
        """Unauthenticated user cannot complete a CharacterQuest"""
        self.client.logout()
        response = self.client.post(self.complete_url1)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class QuestViewSetTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.character = Character.objects.create(name="Hero", can_link=True)
        cls.user = User.objects.create_user(
            email="testuser@example.com", password="pass1234"
        )
        cls.player = cls.user.player

        cls.quest1 = Quest.objects.create(name="Quest 1", description="Test quest 1")
        cls.quest2 = Quest.objects.create(name="Quest 2", description="Test quest 2")

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.list_url = reverse("quest-list")  # DRF router name
        self.eligible_url = reverse("quest-eligible")  # DRF router action

    def test_list_quests(self):
        """GET /quests/ should return all quests"""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]), 2)

        names = [q["name"] for q in response.data["results"]]
        self.assertIn("Quest 1", names)
        self.assertIn("Quest 2", names)

    def test_eligible_quests_success(self):
        """GET /quests/eligible/ should return eligible quests for active character"""
        response = self.client.get(self.eligible_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("eligible_quests", response.data)
        # Depending on check_quest_eligibility logic, may need to adjust expected results
        names = [q["name"] for q in response.data["eligible_quests"]]
        self.assertTrue(set(names).issubset({"Quest 1", "Quest 2"}))

    def test_eligible_quests_no_active_character(self):
        """Eligible returns 400 if user has no active character"""
        PlayerCharacterLink.objects.filter(player=self.player).delete()
        response = self.client.get(self.eligible_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_authentication_required_list(self):
        """Unauthenticated user cannot list quests"""
        self.client.logout()
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authentication_required_eligible(self):
        """Unauthenticated user cannot access eligible quests"""
        self.client.logout()
        response = self.client.get(self.eligible_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
