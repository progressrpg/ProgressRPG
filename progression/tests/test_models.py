from progression.models import (
    Category,
    Role,
    PlayerSkill,
    CharacterSkill,
    PlayerActivity,
    CharacterQuest,
    Project,
    Task,
)
from .base import BaseTestCase


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
