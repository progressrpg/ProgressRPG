from datetime import date, datetime, time, timedelta

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
from locations.constants import PROJECT_SRID


class WorkActivitiesForTests(TestCase):
    def setUp(self):
        self.character = Character.objects.create(
            given_name="Marigold", location=Point(0, 0, srid=PROJECT_SRID)
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
            given_name="Oswin", location=Point(0, 0, srid=PROJECT_SRID)
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
            location=Point(0, 0, srid=PROJECT_SRID),
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
            given_name="Della", location=Point(0, 0, srid=PROJECT_SRID)
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


class BehaviourSyncTestCase(TestCase):
    """
    Shared setup for SyncToNowTests/AdvanceTests/InterruptCurrentActivityTests:
    a character with no scheduled activities yet, and a helper to create one
    at an offset from the real `timezone.now()` - get_current_activity (which
    all three functions under test go through) always reads the real clock,
    not a passed-in `now`, so fixture times have to be anchored there rather
    than to a fixed date the way GenerateDayWorkActivityTests' are.
    """

    def setUp(self):
        self.character = Character.objects.create(
            given_name="Rowan", location=Point(0, 0, srid=PROJECT_SRID)
        )
        self.activity_definition = ActivityDefinition.objects.create(
            name="Chores", kind=ActivityDefinition.Kind.WORK
        )

    def _activity(self, start, end, **kwargs):
        return CharacterActivity.objects.create(
            character=self.character,
            activity_definition=self.activity_definition,
            scheduled_start=start,
            scheduled_end=end,
            **kwargs,
        )


class SyncToNowTests(BehaviourSyncTestCase):
    def test_current_activity_with_started_at_set_is_returned_as_is(self):
        now = timezone.now()
        started = now - timedelta(minutes=5)
        current = self._activity(
            now - timedelta(minutes=10), now + timedelta(minutes=10), started_at=started
        )

        result = self.character.behaviour.sync_to_now()

        self.assertEqual(result, current)
        current.refresh_from_db()
        self.assertEqual(current.started_at, started)

    def test_current_activity_with_no_started_at_is_backfilled_to_scheduled_start(self):
        now = timezone.now()
        window_start = now - timedelta(minutes=10)
        current = self._activity(window_start, now + timedelta(minutes=10))
        self.assertIsNone(current.started_at)

        result = self.character.behaviour.sync_to_now()

        self.assertEqual(result, current)
        current.refresh_from_db()
        self.assertEqual(current.started_at, window_start)

    def test_no_current_activity_returns_the_next_upcoming_one(self):
        now = timezone.now()
        upcoming = self._activity(
            now + timedelta(minutes=5), now + timedelta(minutes=15)
        )

        result = self.character.behaviour.sync_to_now()

        self.assertEqual(result, upcoming)

    def test_no_current_and_no_upcoming_returns_none(self):
        result = self.character.behaviour.sync_to_now()

        self.assertIsNone(result)

    def test_ended_but_incomplete_activity_is_completed_past_before_the_lookup(self):
        now = timezone.now()
        ended = self._activity(now - timedelta(minutes=20), now - timedelta(minutes=10))
        self.assertFalse(ended.is_complete)

        self.character.behaviour.sync_to_now()

        ended.refresh_from_db()
        self.assertTrue(ended.is_complete)
        self.assertEqual(ended.completed_at, ended.scheduled_end)


class AdvanceTests(BehaviourSyncTestCase):
    def test_current_activity_is_force_completed_via_complete_now(self):
        now = timezone.now()
        current = self._activity(
            now - timedelta(minutes=10), now + timedelta(minutes=10)
        )
        original_scheduled_end = current.scheduled_end

        self.character.behaviour.advance()

        current.refresh_from_db()
        self.assertTrue(current.is_complete)
        self.assertIsNotNone(current.completed_at)
        # complete_now() doesn't touch scheduled_end - only started_at/
        # completed_at/is_complete/duration.
        self.assertEqual(current.scheduled_end, original_scheduled_end)

    def test_next_activitys_started_at_backfill_branch_is_unreachable_here(self):
        """
        advance() has a branch meant to backfill `nxt.started_at` when
        `nxt.scheduled_start <= now`, but it can't actually fire via this
        code path: `current` is only ever selected when
        `current.scheduled_end > now` (see the query above), and `nxt` is
        only ever selected when `nxt.scheduled_start >= current.scheduled_end`
        - so `nxt.scheduled_start > now` holds transitively by the time the
        branch's own condition is checked. Documented as a dead branch
        rather than "fixed" - changing the selection logic is a behaviour
        change outside a test-coverage pass's scope.
        """
        now = timezone.now()
        current = self._activity(
            now - timedelta(minutes=10), now + timedelta(minutes=10)
        )
        nxt = self._activity(
            current.scheduled_end, current.scheduled_end + timedelta(minutes=10)
        )
        self.assertIsNone(nxt.started_at)

        result = self.character.behaviour.advance()

        self.assertEqual(result, nxt)
        nxt.refresh_from_db()
        # Not backfilled - see docstring.
        self.assertIsNone(nxt.started_at)

    def test_no_current_in_window_falls_through_to_sync_to_now(self):
        now = timezone.now()
        upcoming = self._activity(
            now + timedelta(minutes=5), now + timedelta(minutes=15)
        )

        result = self.character.behaviour.advance()

        self.assertEqual(result, upcoming)

    def test_no_next_activity_after_the_current_one_returns_none(self):
        now = timezone.now()
        self._activity(now - timedelta(minutes=10), now + timedelta(minutes=10))

        result = self.character.behaviour.advance()

        self.assertIsNone(result)


class InterruptCurrentActivityTests(BehaviourSyncTestCase):
    def test_splits_the_current_activity_into_a_completed_and_a_fresh_one(self):
        now = timezone.now()
        original = self._activity(
            now - timedelta(minutes=10), now + timedelta(minutes=20)
        )

        new_activity = self.character.behaviour.interrupt_current_activity()

        self.assertIsNotNone(new_activity)
        original.refresh_from_db()
        self.assertTrue(original.is_complete)

        self.assertEqual(new_activity.character, self.character)
        self.assertEqual(new_activity.activity_definition, self.activity_definition)
        self.assertEqual(new_activity.scheduled_end, original.scheduled_end)
        self.assertFalse(new_activity.is_complete)
        self.assertIsNotNone(new_activity.started_at)
        self.assertAlmostEqual(new_activity.started_at, now, delta=timedelta(seconds=5))

    def test_no_current_activity_returns_none(self):
        result = self.character.behaviour.interrupt_current_activity()

        self.assertIsNone(result)

    def test_an_already_complete_current_activity_returns_none_and_creates_nothing(
        self,
    ):
        now = timezone.now()
        self._activity(
            now - timedelta(minutes=10),
            now + timedelta(minutes=10),
            is_complete=True,
        )
        before_count = CharacterActivity.objects.filter(
            character=self.character
        ).count()

        result = self.character.behaviour.interrupt_current_activity()

        self.assertIsNone(result)
        self.assertEqual(
            CharacterActivity.objects.filter(character=self.character).count(),
            before_count,
        )

    def test_boost_ended_argument_is_currently_unread_and_changes_nothing(self):
        """
        boost_ended is accepted but never read inside the function body -
        pins that current no-op status (not a fix) so a reader doesn't have
        to trace the implementation to find out.
        """
        now = timezone.now()
        self._activity(now - timedelta(minutes=10), now + timedelta(minutes=20))

        with_true = self.character.behaviour.interrupt_current_activity(
            boost_ended=True
        )

        self.assertIsNotNone(with_true)

        # Fresh activity for a second, independent comparison.
        self._activity(now - timedelta(minutes=10), now + timedelta(minutes=20))
        with_false = self.character.behaviour.interrupt_current_activity(
            boost_ended=False
        )

        self.assertIsNotNone(with_false)
        self.assertEqual(with_true.activity_definition, with_false.activity_definition)
