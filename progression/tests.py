# progression/tests.py
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from unittest import skip

from .models import (
    Category,
    Role,
    PlayerSkill,
    CharacterSkill,
    PlayerActivity,
    CharacterQuest,
    Project,
    Task,
)
from .utils import copy_quest

from character.models import Character
from gameplay.models import Quest
from users.models import Player

import logging

User = get_user_model()

logger = logging.getLogger("general")


class BaseTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="test@test.com", password="pass")
        self.character = Character.objects.create(
            name="Test Character",
        )
        self.profile, _ = Profile.objects.get_or_create(
            user=self.user,
        )
        self.profile.name = "Test Profile"


class GroupModelTests(BaseTestCase):
    def setUp(self):
        super().setUp()

    def test_category_rename(self):
        category = Category.objects.create(
            profile=self.profile,
            name="Old Name",
        )

        category.rename("New Name")
        category.refresh_from_db()

        self.assertEqual(category.name, "New Name")


class SkillModelTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.category = Category.objects.create(
            profile=self.profile,
            name="Productivity",
        )

    def test_player_skill_rename(self):
        skill = PlayerSkill.objects.create(
            profile=self.profile,
            name="Focus",
            category=self.category,
        )

        skill.rename("Deep Focus")
        skill.refresh_from_db()

        self.assertEqual(skill.name, "Deep Focus")

    def test_character_skill_roles(self):
        role1 = Role.objects.create(character=self.character, name="Leader")
        role2 = Role.objects.create(character=self.character, name="Diplomat")

        skill = CharacterSkill.objects.create(
            character=self.character,
            name="Communication",
        )
        skill.roles.add(role1, role2)

        self.assertEqual(skill.roles.count(), 2)
        self.assertIn(role1, skill.roles.all())
        self.assertIn(role2, skill.roles.all())


class ActivityModelTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.category = Category.objects.create(
            profile=self.profile,
            name="Work",
        )
        self.skill = PlayerSkill.objects.create(
            profile=self.profile,
            name="Coding",
            category=self.category,
        )

    def test_activity_start(self):
        activity = PlayerActivity.objects.create(
            profile=self.profile,
            name="Write tests",
        )

        started_at = activity.start()

        self.assertIsNotNone(started_at)
        self.assertIsNotNone(activity.started_at)

    def test_activity_complete_updates_skill(self):
        activity = PlayerActivity.objects.create(
            profile=self.profile,
            name="Write tests",
            skill=self.skill,
            duration=30,
        )

        completed_at = activity.complete()

        self.assertIsNotNone(completed_at)
        self.assertTrue(activity.is_complete)

        # skill totals are dynamic via records
        self.assertEqual(self.skill.total_time, 30)
        self.assertEqual(self.skill.records.count(), 1)


class CharacterQuestTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.role = Role.objects.create(
            character=self.character,
            name="Adventurer",
        )
        self.skill = CharacterSkill.objects.create(
            character=self.character,
            name="Survival",
        )
        self.skill.roles.add(self.role)

    def test_character_quest_complete(self):
        quest = CharacterQuest.objects.create(
            character=self.character,
            name="Forage for food",
            skill=self.skill,
            duration=45,
        )

        quest.complete()

        self.assertTrue(quest.is_complete)
        self.assertEqual(self.skill.total_time, 45)
        self.assertEqual(self.skill.records.count(), 1)


class ProjectTaskTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.project = Project.objects.create(
            profile=self.profile,
            name="Progress RPG",
            description="Build the app",
        )
        self.task = Task.objects.create(
            profile=self.profile,
            project=self.project,
            name="Write models",
            description="Django models",
        )

    def test_task_activity_total(self):
        # Activity linked only to task
        activity = PlayerActivity.objects.create(
            profile=self.profile,
            name="Task work",
            task=self.task,
            duration=30,
        )
        activity.complete()

        self.assertEqual(self.task.total_time, 30)
        self.assertEqual(self.task.total_records, 1)

        # Project total should include task activities
        self.assertEqual(self.project.total_time, 30)
        self.assertEqual(self.project.total_records, 1)

    def test_project_activity_total(self):
        # Activity linked only to project (not a task)
        activity = PlayerActivity.objects.create(
            profile=self.profile,
            name="Project work",
            project=self.project,
            duration=50,
        )
        activity.complete()

        self.assertEqual(self.project.total_time, 50)
        self.assertEqual(self.project.total_records, 1)


class UtilityCopyQuest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.character = Character.objects.create(name="Bob", sex="Male")
        cls.quest = Quest.objects.create(name="Test quest")

    def test_copy_quest(self):
        cq = copy_quest(self.character, self.quest)
        self.assertIsInstance(cq, CharacterQuest)
