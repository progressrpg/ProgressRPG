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
        self.player, _ = Player.objects.get_or_create(
            user=self.user,
        )
        self.player.name = "Test Player"


class GroupModelTests(BaseTestCase):
    def setUp(self):
        super().setUp()

    def test_category_rename(self):
        category = Category.objects.create(
            player=self.player,
            name="Old Name",
        )

        category.rename("New Name")
        category.refresh_from_db()

        self.assertEqual(category.name, "New Name")


class SkillModelTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.category = Category.objects.create(
            player=self.player,
            name="Productivity",
        )

    def test_player_skill_rename(self):
        skill = PlayerSkill.objects.create(
            player=self.player,
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
            player=self.player,
            name="Work",
        )
        self.skill = PlayerSkill.objects.create(
            player=self.player,
            name="Coding",
            category=self.category,
        )

    def test_activity_start(self):
        activity = PlayerActivity.objects.create(
            player=self.player,
            name="Write tests",
        )

        started_at = activity.start()

        self.assertIsNotNone(started_at)
        self.assertIsNotNone(activity.started_at)

    def test_activity_complete_updates_skill(self):
        activity = PlayerActivity.objects.create(
            player=self.player,
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

    def test_activity_infers_group_key_from_exact_case_insensitive_match(self):
        PlayerActivity.objects.create(
            player=self.player,
            name="Deep Work",
            group_key="deep-work-session",
        )
        PlayerActivity.objects.create(
            player=self.player,
            name="deep work",
            group_key="deep-work-session",
        )
        PlayerActivity.objects.create(
            player=self.player,
            name="Deep Work",
            group_key="other-group",
        )

        activity = PlayerActivity.objects.create(
            player=self.player,
            name="DEEP WORK",
        )

        self.assertEqual(activity.group_key, "deep-work-session")

    def test_activity_infers_group_key_from_dominant_similar_titles(self):
        recent_time = timezone.now() - timedelta(days=5)
        for name in [
            "Write docs",
            "Write documentation",
            "Write docs sprint",
        ]:
            activity = PlayerActivity.objects.create(
                player=self.player,
                name=name,
                group_key="docs-writing",
            )
            PlayerActivity.objects.filter(pk=activity.pk).update(
                last_updated=recent_time
            )

        older_activity = PlayerActivity.objects.create(
            player=self.player,
            name="Write document",
            group_key="other-group",
        )
        PlayerActivity.objects.filter(pk=older_activity.pk).update(
            last_updated=timezone.now() - timedelta(days=180)
        )

        activity = PlayerActivity.objects.create(
            player=self.player,
            name="Write doc",
        )

        self.assertEqual(activity.group_key, "docs-writing")

    def test_activity_leaves_group_key_null_when_similar_signal_is_weak(self):
        PlayerActivity.objects.create(
            player=self.player,
            name="Write docs",
            group_key="docs-writing",
        )
        PlayerActivity.objects.create(
            player=self.player,
            name="Write document",
            group_key="document-work",
        )

        activity = PlayerActivity.objects.create(
            player=self.player,
            name="Write doc",
        )

        self.assertIsNone(activity.group_key)


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
            player=self.player,
            name="Progress RPG",
            description="Build the app",
        )
        self.task = Task.objects.create(
            player=self.player,
            project=self.project,
            name="Write models",
            description="Django models",
        )

    def test_task_activity_total(self):
        # Activity linked only to task
        activity = PlayerActivity.objects.create(
            player=self.player,
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
            player=self.player,
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
