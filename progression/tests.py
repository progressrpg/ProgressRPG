# progression/tests.py
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from unittest import skip

from .models import Activity, CharacterQuest
from .utils import copy_quest

from character.models import Character
from gameplay.models import Quest

import logging

User = get_user_model()

logger = logging.getLogger("django")


class ActivityCreation(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.character = Character.objects.create(name="Bob", sex="Male")
        user = User.objects.create_user(
            email="testuser1@example.com", password="testpassword123"
        )
        cls.profile = user.profile

    def test_activity_create(self):
        activity = Activity.objects.create(name="Activity test", profile=self.profile)
        self.assertIsInstance(activity, Activity)
        self.assertEqual("Activity test", activity.name)


class ActivityMethods(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.character = Character.objects.create(name="Bob", sex="Male")
        user = User.objects.create_user(
            email="testuser1@example.com", password="testpassword123"
        )
        cls.activity = Activity.objects.create(name="test", profile=user.profile)

    def test_activity_rename(self):
        self.activity.rename("test rename")
        self.assertEqual("test rename", self.activity.name)

    def test_add_time(self):
        self.activity.add_time(5)
        self.assertEqual(5, self.activity.duration)

    def test_new_time(self):
        self.activity.new_time(5)
        self.assertEqual(5, self.activity.duration)

    def test_start(self):
        timestamp = self.activity.start()
        self.assertEqual(timestamp, self.activity.started_at)

    def test_complete(self):
        timestamp = self.activity.complete()
        self.assertEqual(timestamp, self.activity.completed_at)
        self.assertEqual(True, self.activity.is_complete)

    def test_is_private(self):
        self.activity.is_private = True
        self.activity.save(update_fields=["is_private"])
        self.assertEqual("Private activity", str(self.activity))


class CharacterQuestCreation(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.character = Character.objects.create(name="Bob", sex="Male")

    def test_character_quest_creation(self):
        character_quest = CharacterQuest.objects.create(
            name="test", character=self.character
        )
        self.assertEqual("test", character_quest.name)
        self.assertEqual(self.character, character_quest.character)


class UtilityCopyQuest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.character = Character.objects.create(name="Bob", sex="Male")
        cls.quest = Quest.objects.create(name="Test quest")

    def test_copy_quest(self):
        cq = copy_quest(self.character, self.quest)
        self.assertIsInstance(cq, CharacterQuest)
