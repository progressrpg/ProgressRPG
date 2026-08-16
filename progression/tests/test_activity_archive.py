from datetime import date, timedelta

from django.contrib.gis.geos import Point
from django.test import TestCase
from django.utils import timezone

from character.models import Character
from core.models import GameSettings
from progression.models import (
    ActivityDefinition,
    CharacterActivity,
    CharacterActivityArchive,
    CharacterSkill,
    Role,
    SkillDefinition,
    character_total_skill_xp,
)
from progression.tasks import compact_character_activities


def _make_activity(character, activity_definition, *, completed_at, duration=600):
    return CharacterActivity.objects.create(
        character=character,
        activity_definition=activity_definition,
        is_complete=True,
        started_at=completed_at - timedelta(seconds=duration),
        completed_at=completed_at,
        duration=duration,
    )


class CharacterActivityArchiveAggregationTests(TestCase):
    """
    Once compaction rolls old CharacterActivity rows into
    CharacterActivityArchive, every duration/XP aggregate that used to read
    CharacterActivity alone must still return the same totals.
    """

    def setUp(self):
        self.character = Character.objects.create(
            given_name="Aggregatia", location=Point(0, 0, srid=3857)
        )
        self.role = Role.objects.create(name="Farmer")
        self.skill = SkillDefinition.objects.create(name="Farming", role=self.role)
        self.activity_definition = ActivityDefinition.objects.create(
            name="tending crops",
            kind=ActivityDefinition.Kind.WORK,
            skill=self.skill,
        )
        GameSettings.current()

    def test_character_total_skill_xp_sums_live_and_archived_duration(self):
        _make_activity(
            self.character, self.activity_definition, completed_at=timezone.now()
        )
        CharacterActivityArchive.objects.create(
            character=self.character,
            activity_definition=self.activity_definition,
            month=date(2026, 1, 1),
            total_duration=400,
            record_count=2,
        )

        # 600 (live) + 400 (archived) seconds at the default 1.0 xp/sec rate.
        self.assertEqual(character_total_skill_xp(self.character), 1000)

    def test_character_total_skill_xp_query_count_stays_bounded(self):
        # One aggregate against CharacterActivity, one against
        # CharacterActivityArchive, one GameSettings lookup for the XP rate
        # - guards against the archive lookup silently growing more
        # expensive (e.g. N+1) as it's extended.
        with self.assertNumQueries(3):
            character_total_skill_xp(self.character)

    def test_role_proficiency_sums_live_and_archived_duration(self):
        CharacterActivityArchive.objects.create(
            character=self.character,
            activity_definition=self.activity_definition,
            month=date(2026, 1, 1),
            total_duration=250,
            record_count=1,
        )

        self.assertEqual(self.role.proficiency_for(self.character), 250)

    def test_character_skill_total_time_and_records_include_archive(self):
        _make_activity(
            self.character, self.activity_definition, completed_at=timezone.now()
        )
        CharacterActivityArchive.objects.create(
            character=self.character,
            activity_definition=self.activity_definition,
            month=date(2026, 1, 1),
            total_duration=300,
            record_count=3,
        )
        character_skill = CharacterSkill.objects.create(
            character=self.character, skill_definition=self.skill
        )

        self.assertEqual(character_skill.total_time, 900)
        self.assertEqual(character_skill.total_records, 4)

    def test_character_total_activities_includes_archive(self):
        _make_activity(
            self.character, self.activity_definition, completed_at=timezone.now()
        )
        CharacterActivityArchive.objects.create(
            character=self.character,
            activity_definition=self.activity_definition,
            month=date(2026, 1, 1),
            total_duration=300,
            record_count=5,
        )

        self.assertEqual(self.character.total_activities, 6)


class CompactCharacterActivitiesTaskTests(TestCase):
    def setUp(self):
        self.character = Character.objects.create(
            given_name="Compactia", location=Point(0, 0, srid=3857)
        )
        self.activity_definition = ActivityDefinition.objects.create(
            name="hauling water", kind=ActivityDefinition.Kind.WORK
        )
        self.other_activity_definition = ActivityDefinition.objects.create(
            name="chopping wood", kind=ActivityDefinition.Kind.WORK
        )
        settings = GameSettings.current()
        settings.activity_compaction_cutoff_days = 90
        settings.save()

        self.now = timezone.now()
        self.old_completed_at = self.now - timedelta(days=120)
        self.recent_completed_at = self.now - timedelta(days=5)

    def test_old_completed_activities_are_archived_and_deleted(self):
        old_activity = _make_activity(
            self.character,
            self.activity_definition,
            completed_at=self.old_completed_at,
            duration=500,
        )

        result = compact_character_activities()

        self.assertEqual(result["archived_groups"], 1)
        self.assertEqual(result["archived_rows"], 1)
        self.assertFalse(CharacterActivity.objects.filter(pk=old_activity.pk).exists())
        archive = CharacterActivityArchive.objects.get(
            character=self.character, activity_definition=self.activity_definition
        )
        self.assertEqual(archive.total_duration, 500)
        self.assertEqual(archive.record_count, 1)
        self.assertEqual(archive.month, self.old_completed_at.date().replace(day=1))

    def test_recent_completed_activities_are_left_untouched(self):
        recent_activity = _make_activity(
            self.character,
            self.activity_definition,
            completed_at=self.recent_completed_at,
        )

        result = compact_character_activities()

        self.assertEqual(result["archived_groups"], 0)
        self.assertTrue(
            CharacterActivity.objects.filter(pk=recent_activity.pk).exists()
        )
        self.assertFalse(CharacterActivityArchive.objects.exists())

    def test_in_progress_activities_are_never_archived_regardless_of_age(self):
        in_progress = CharacterActivity.objects.create(
            character=self.character,
            activity_definition=self.activity_definition,
            is_complete=False,
            started_at=self.old_completed_at,
        )

        compact_character_activities()

        self.assertTrue(CharacterActivity.objects.filter(pk=in_progress.pk).exists())
        self.assertFalse(CharacterActivityArchive.objects.exists())

    def test_rerunning_the_task_accumulates_rather_than_overwrites(self):
        _make_activity(
            self.character,
            self.activity_definition,
            completed_at=self.old_completed_at,
            duration=200,
        )
        compact_character_activities()

        _make_activity(
            self.character,
            self.activity_definition,
            completed_at=self.old_completed_at + timedelta(hours=1),
            duration=300,
        )
        compact_character_activities()

        archive = CharacterActivityArchive.objects.get(
            character=self.character, activity_definition=self.activity_definition
        )
        self.assertEqual(archive.total_duration, 500)
        self.assertEqual(archive.record_count, 2)

    def test_distinct_activity_definitions_in_the_same_month_archive_separately(self):
        _make_activity(
            self.character,
            self.activity_definition,
            completed_at=self.old_completed_at,
            duration=100,
        )
        _make_activity(
            self.character,
            self.other_activity_definition,
            completed_at=self.old_completed_at,
            duration=150,
        )

        compact_character_activities()

        self.assertEqual(CharacterActivityArchive.objects.count(), 2)
        first = CharacterActivityArchive.objects.get(
            activity_definition=self.activity_definition
        )
        second = CharacterActivityArchive.objects.get(
            activity_definition=self.other_activity_definition
        )
        self.assertEqual(first.total_duration, 100)
        self.assertEqual(second.total_duration, 150)

    def test_deleting_character_cascades_to_archive_rows(self):
        _make_activity(
            self.character,
            self.activity_definition,
            completed_at=self.old_completed_at,
        )
        compact_character_activities()
        self.assertTrue(CharacterActivityArchive.objects.exists())

        self.character.delete()

        self.assertFalse(CharacterActivityArchive.objects.exists())

    def test_deleting_activity_definition_referenced_by_archive_is_protected(self):
        from django.db.models import ProtectedError

        _make_activity(
            self.character,
            self.activity_definition,
            completed_at=self.old_completed_at,
        )
        compact_character_activities()

        with self.assertRaises(ProtectedError):
            self.activity_definition.delete()
