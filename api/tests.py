from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from unittest import skip

from character.models import Character, PlayerCharacterLink
from gameplay.models import Quest
from progression.models import CharacterQuest

User = get_user_model()


class MeViewTest(APITestCase):
    def setUp(self):
        self.character = Character.objects.create(name="Hero", can_link=True)
        self.user = User.objects.create_user(
            email="test@example.com", password="testpassword123"
        )
        self.url = reverse("me")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_me_view_authenticated(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["user"]["email"], self.user.email)

    def test_me_view_unauthenticated(self):
        self.client.force_authenticate(user=None)  # remove authentication
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class CharacterQuestViewSetTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.character = Character.objects.create(name="Hero", can_link=True)

        cls.user = User.objects.create_user(
            email="testuser@example.com", password="pass1234"
        )
        cls.profile = cls.user.profile

        cls.quest1 = Quest.objects.create(name="Quest 1", description="Test quest 1")
        cls.quest2 = Quest.objects.create(name="Quest 2", description="Test quest 2")

        cls.char_quest1 = CharacterQuest.objects.create(
            character=cls.character,
            name=cls.quest1.name,
            description=cls.quest1.description,
            quest_duration=300,
        )
        cls.char_quest2 = CharacterQuest.objects.create(
            character=cls.character,
            name=cls.quest2.name,
            description=cls.quest2.description,
            quest_duration=600,
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
        PlayerCharacterLink.objects.filter(profile=self.profile).delete()
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
        cls.profile = cls.user.profile

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
        self.assertIn("quests", response.data)
        self.assertEqual(len(response.data["quests"]), 2)
        names = [q["name"] for q in response.data["quests"]]
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
        PlayerCharacterLink.objects.filter(profile=self.profile).delete()
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


class QuestTimerViewSetTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.character = Character.objects.create(name="Hero", can_link=True)
        cls.user = User.objects.create_user(
            email="testuser@example.com", password="pass1234"
        )
        cls.profile = cls.user.profile
        cls.quest = Quest.objects.create(name="Test Quest", description="A test quest")

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.url = reverse(
            "questtimer-change-quest", args=[self.character.quest_timer.id]
        )

    def test_requires_authentication(self):
        self.client.logout()
        response = self.client.post(
            self.url, {"quest_id": self.quest.id, "duration": 60}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_change_quest_success(self):
        response = self.client.post(
            self.url, {"quest_id": self.quest.id, "duration": 60}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["quest_timer"]["duration"], 60)

    def test_invalid_character_access(self):
        other_character = Character.objects.create(name="Villain", can_link=True)
        other_user = User.objects.create_user(
            email="other@example.com", password="pass1234"
        )
        other_profile = other_user.profile
        other_character.save()

        url = reverse("questtimer-change-quest", args=[other_character.quest_timer.id])
        response = self.client.post(url, {"quest_id": self.quest.id, "duration": 60})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_invalid_duration(self):
        response = self.client.post(
            self.url, {"quest_id": self.quest.id, "duration": "notanumber"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Duration must be an integer.", response.data["error"])

    def test_missing_quest_id(self):
        response = self.client.post(self.url, {"duration": 60})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_quest_id(self):
        response = self.client.post(self.url, {"quest_id": 9999, "duration": 60})
        self.assertIn(
            response.status_code,
            [status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND],
        )
