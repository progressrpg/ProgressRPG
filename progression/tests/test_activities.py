from datetime import timedelta

from django.utils import timezone

from progression.models import Category, PlayerActivity, PlayerSkill
from .base import BaseTestCase


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
