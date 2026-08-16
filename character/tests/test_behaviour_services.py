from datetime import date, datetime, time

from django.contrib.gis.geos import Point
from django.test import TestCase
from django.utils import timezone

from character.models import Character, CharacterLocation
from character.services.behaviour_services import _FIXED_KINDS
from character.utils import work_activities_for
from locations.models import Building
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
            given_name="Marigold", location=Point(0, 0, srid=3857)
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


def create_activity_catalog():
    """
    Minimal ActivityDefinition catalog generate_day needs to build a full
    day: one skill-less definition per fixed block kind, plus two skill-less
    "work" definitions (rng.sample needs a population of at least 2 to fill
    both work blocks).
    """
    for kind in _FIXED_KINDS:
        ActivityDefinition.objects.create(name=f"{kind} block", kind=kind)
    ActivityDefinition.objects.create(
        name="general work A", kind=ActivityDefinition.Kind.WORK
    )
    ActivityDefinition.objects.create(
        name="general work B", kind=ActivityDefinition.Kind.WORK
    )


class GenerateDayWorkActivityTests(TestCase):
    def setUp(self):
        self.character = Character.objects.create(
            given_name="Oswin", location=Point(0, 0, srid=3857)
        )
        create_activity_catalog()

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

    def test_late_building_hours_extend_the_work_block_past_the_default_workday(self):
        # Inn hours run 06:00-23:00 (see Building.BUILDING_TYPE_HOURS) - well
        # past generate_day's old fixed 17:00 work cutoff. An inn worker
        # should still be scheduled as "working" in the evening instead of
        # falling through to the fixed leisure block (issue: characters
        # assigned to the inn showed as "Relaxing" during their shift).
        inn = Building.objects.create(
            name="The Tipsy Griffin",
            building_type="inn",
            location=Point(0, 0, srid=3857),
        )
        CharacterLocation.objects.create(
            character=self.character,
            location=inn,
            role=CharacterLocation.Role.WORK,
            is_primary=True,
        )

        self.character.behaviour.generate_day(date(2026, 1, 5))

        evening = timezone.make_aware(datetime.combine(date(2026, 1, 5), time(21, 0)))
        activity_at_evening = CharacterActivity.objects.get(
            character=self.character,
            scheduled_start__lte=evening,
            scheduled_end__gt=evening,
        )
        self.assertEqual(activity_at_evening.activity_definition.kind, "work")


class DeleteDayTests(TestCase):
    def setUp(self):
        self.character = Character.objects.create(
            given_name="Della", location=Point(0, 0, srid=3857)
        )
        create_activity_catalog()

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
