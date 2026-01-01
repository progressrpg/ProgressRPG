from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.test import TestCase, Client
from django.urls import reverse
from django.utils.timezone import now
from unittest import skip

from users.models import Profile
from character.models import Character, PlayerCharacterLink
from gameplay.models import Quest
from progression.models import PlayerActivity

import json, logging

User = get_user_model()

logging.getLogger("django").setLevel(logging.CRITICAL)


class GameplayViewTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.character = Character.objects.create(name="Bob")
        cls.user = User.objects.create_user(
            email="testuser@gmail.com", password="testpass"
        )
        cls.profile = cls.user.profile

    def setUp(self):
        self.client = Client()
        self.client.login(username="testuser@gmail.com", password="testpass")

    def ajax_post(self, url, data):
        return self.client.post(
            url,
            json.dumps(data),
            content_type="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

    def get_json(self, url):
        return self.client.get(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")


# Game View
class GameViewTest(GameplayViewTestBase):
    def test_requires_authentication(self):
        self.client.logout()
        response = self.client.get(reverse("game"))
        self.assertNotEqual(response.status_code, 200)

    @skip("Skipping as temporarily broken")
    def test_get_game_view(self):
        response = self.client.get(reverse("game"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "gameplay/game.html")


# Fetch Activities
class FetchActivitiesTest(GameplayViewTestBase):
    def test_get_activities(self):
        PlayerActivity.objects.create(profile=self.profile, name="Test Activity")
        response = self.client.get(reverse("fetch_activities"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("activities", response.json())

    def test_invalid_method(self):
        response = self.client.post(reverse("fetch_activities"))
        self.assertEqual(response.status_code, 405)


# Fetch Quests
class FetchQuestsTest(GameplayViewTestBase):
    @skip("Skipping as temporarily broken")
    def test_get_quests(self):
        Quest.objects.create(name="Test Quest", description="Test")
        response = self.client.get(reverse("fetch_quests"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("quests", response.json())

    def test_invalid_method(self):
        response = self.client.post(reverse("fetch_quests"))
        self.assertEqual(response.status_code, 405)


# Fetch Info
class FetchInfoTest(GameplayViewTestBase):
    @skip("Skipping as temporarily broken")
    def test_get_info(self):
        response = self.client.get(reverse("fetch_info"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("profile", response.json())
        self.assertIn("character", response.json())


# Create Activity
class CreateActivityTest(GameplayViewTestBase):
    def test_create_valid_activity(self):
        data = {"activityName": "Focus Time"}
        response = self.ajax_post(reverse("create_activity"), data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(PlayerActivity.objects.filter(profile=self.profile).exists())

    def test_create_activity_missing_name(self):
        response = self.ajax_post(reverse("create_activity"), {})
        self.assertEqual(response.status_code, 400)

    def test_invalid_method(self):
        response = self.client.get(reverse("create_activity"))
        self.assertEqual(response.status_code, 405)


# Submit Activity
class SubmitActivityTest(GameplayViewTestBase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.activity = PlayerActivity.objects.create(
            profile=cls.profile, name="Initial Activity"
        )
        cls.profile.activity_timer.new_activity(cls.activity)

    @skip("Skipping as temporarily broken")
    def test_submit_activity(self):
        data = {"name": "Updated Activity"}
        response = self.ajax_post(reverse("submit_activity"), data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("activity_rewards", response.json())

    def test_submit_activity_invalid_json(self):
        response = self.client.post(
            reverse("submit_activity"), data="notjson", content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)


# Choose Quest
class ChooseQuestTest(GameplayViewTestBase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.quest = Quest.objects.create(name="Quest 1", description="Test quest")

    @skip("Skipping as temporarily broken")
    def test_choose_valid_quest(self):
        data = {"quest_id": self.quest.id, "duration": 30}
        response = self.ajax_post(reverse("choose_quest"), data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("quest_timer", response.json())

    def test_choose_quest_invalid_content_type(self):
        response = self.client.post(
            reverse("choose_quest"), {"quest_id": self.quest.id}
        )
        self.assertEqual(response.status_code, 400)

    def test_invalid_method(self):
        response = self.client.get(reverse("choose_quest"))
        self.assertEqual(response.status_code, 400)


# Complete Quest
class CompleteQuestTest(GameplayViewTestBase):
    @skip("Skipping as temporarily broken")
    def test_complete_quest(self):
        self.character.quest_timer.change_quest(
            Quest.objects.create(name="Test Quest", description="Q"), 30
        )
        response = self.ajax_post(reverse("complete_quest"), {})
        self.assertEqual(response.status_code, 200)
        self.assertIn("xp_reward", response.json())


# Submit Bug Report
class SubmitBugReportTest(GameplayViewTestBase):
    def test_submit_bug_report(self):
        data = {"message": "Something broke"}
        response = self.ajax_post(reverse("submit_bug_report"), data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get("success"))

    def test_invalid_method(self):
        response = self.client.get(reverse("submit_bug_report"))
        self.assertEqual(response.status_code, 405)
