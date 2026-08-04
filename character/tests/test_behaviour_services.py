from datetime import date

from django.contrib.gis.geos import Point
from django.test import TestCase

from character.models import Character
from character.utils import work_activities_for
from progression.models import (
    ActivityDefinition,
    CharacterActivity,
    CharacterRole,
    Role,
    SkillDefinition,
    SkillGroup,
)


class WorkActivitiesForTests(TestCase):
    def setUp(self):
        self.character = Character.objects.create(
            first_name="Marigold", location=Point(0, 0, srid=3857)
        )
        self.general_activity = ActivityDefinition.objects.create(
            name="hauling water", kind=ActivityDefinition.Kind.WORK
        )

    def test_general_work_activities_available_without_any_role(self):
        self.assertIn(self.general_activity, work_activities_for(self.character))

    def test_role_linked_activity_excluded_until_role_is_held(self):
        role = Role.objects.create(name="Farmer")
        skill = SkillDefinition.objects.create(name="Farming", role=role)
        role_activity = ActivityDefinition.objects.create(
            name="tending crops", kind=ActivityDefinition.Kind.WORK, skill=skill
        )

        self.assertNotIn(role_activity, work_activities_for(self.character))

        CharacterRole.objects.create(character=self.character, role=role)

        self.assertIn(role_activity, work_activities_for(self.character))

    def test_role_linked_activity_for_a_different_role_stays_excluded(self):
        held_role = Role.objects.create(name="Farmer")
        CharacterRole.objects.create(character=self.character, role=held_role)

        other_role = Role.objects.create(name="Baker")
        other_skill = SkillDefinition.objects.create(name="Baking", role=other_role)
        other_activity = ActivityDefinition.objects.create(
            name="kneading dough", kind=ActivityDefinition.Kind.WORK, skill=other_skill
        )

        self.assertNotIn(other_activity, work_activities_for(self.character))

    def test_activity_gated_above_current_proficiency_is_excluded(self):
        role = Role.objects.create(name="Farmer")
        CharacterRole.objects.create(character=self.character, role=role)
        skill_group = SkillGroup.objects.create(role=role, name="Farming skills")
        gated_skill = SkillDefinition.objects.create(
            name="Advanced farming",
            role=role,
            gate_group=skill_group,
            min_proficiency=10,
        )
        gated_activity = ActivityDefinition.objects.create(
            name="crop rotation planning",
            kind=ActivityDefinition.Kind.WORK,
            skill=gated_skill,
        )

        self.assertNotIn(gated_activity, work_activities_for(self.character))


class GenerateDayWorkActivityTests(TestCase):
    def setUp(self):
        self.character = Character.objects.create(
            first_name="Oswin", location=Point(0, 0, srid=3857)
        )

    def test_work_blocks_use_an_available_activity_definition(self):
        self.character.behaviour.generate_day(date(2026, 1, 5))

        work_activities = CharacterActivity.objects.filter(
            character=self.character, activity_definition__kind="work"
        )
        self.assertTrue(work_activities.exists())

        available_ids = {a.id for a in work_activities_for(self.character)}
        for activity in work_activities:
            self.assertIn(activity.activity_definition_id, available_ids)

    def test_generating_the_same_day_twice_is_deterministic(self):
        self.character.behaviour.generate_day(date(2026, 1, 5))
        first_ids = list(
            CharacterActivity.objects.filter(
                character=self.character, activity_definition__kind="work"
            )
            .order_by("scheduled_start")
            .values_list("activity_definition_id", flat=True)
        )

        self.character.behaviour.generate_day(date(2026, 1, 5))
        second_ids = list(
            CharacterActivity.objects.filter(
                character=self.character, activity_definition__kind="work"
            )
            .order_by("scheduled_start")
            .values_list("activity_definition_id", flat=True)
        )

        self.assertEqual(first_ids, second_ids)


class DeleteDayTests(TestCase):
    def setUp(self):
        self.character = Character.objects.create(
            first_name="Della", location=Point(0, 0, srid=3857)
        )

    def test_delete_day_removes_that_days_activities(self):
        target_date = date(2026, 1, 5)
        self.character.behaviour.generate_day(target_date)
        self.assertTrue(
            CharacterActivity.objects.filter(character=self.character).exists()
        )

        self.character.behaviour.delete_day(target_date)

        self.assertFalse(
            CharacterActivity.objects.filter(character=self.character).exists()
        )
