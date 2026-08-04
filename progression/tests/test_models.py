from progression.models import (
    Category,
    Role,
    SkillGroup,
    SkillDefinition,
    CharacterRole,
    PlayerSkill,
    PlayerActivity,
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

    def test_character_skill_holds_multiple_roles_via_character_role(self):
        role1 = Role.objects.create(name="Leader")
        role2 = Role.objects.create(name="Diplomat")

        CharacterRole.objects.create(character=self.character, role=role1)
        CharacterRole.objects.create(character=self.character, role=role2)

        held_roles = Role.objects.filter(character_roles__character=self.character)
        self.assertEqual(held_roles.count(), 2)
        self.assertIn(role1, held_roles)
        self.assertIn(role2, held_roles)


class RoleSkillGroupProficiencyTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.role = Role.objects.create(name="Adventurer")
        self.skill_group = SkillGroup.objects.create(
            role=self.role, name="Survival skills"
        )
        self.gated_skill_definition = SkillDefinition.objects.create(
            name="Advanced foraging",
            role=self.role,
            gate_group=self.skill_group,
            min_proficiency=10,
        )
        self.skill_definition = SkillDefinition.objects.create(
            name="Survival",
            role=self.role,
            gate_group=self.skill_group,
        )
        self.general_skill_definition = SkillDefinition.objects.create(
            name="Reading",
        )

    def test_skill_definition_without_gate_is_always_unlocked(self):
        self.assertTrue(self.skill_definition.is_unlocked_for(self.character))
        self.assertTrue(self.general_skill_definition.is_unlocked_for(self.character))

    def test_gated_skill_definition_locked_with_no_proficiency_yet(self):
        # No CharacterActivity records feed CharacterSkill proficiency yet -
        # that lands with the points economy rework (#691), which derives
        # skill XP from CharacterActivity. Until then, a gated skill stays
        # locked and proficiency reads as zero.
        self.assertFalse(self.gated_skill_definition.is_unlocked_for(self.character))
        self.assertEqual(self.role.proficiency_for(self.character), 0)
        self.assertEqual(self.skill_group.proficiency_for(self.character), 0)


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
