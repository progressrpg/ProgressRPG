from django.contrib.auth import get_user_model

from progression.models import Activity, Category, PlayerActivity, PlayerSkill
from users.models import Player
from .base import BaseTestCase

User = get_user_model()


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

    def test_creating_a_session_resolves_a_case_insensitive_match(self):
        first = PlayerActivity.objects.create(player=self.player, name="Deep Work")
        second = PlayerActivity.objects.create(player=self.player, name="deep work")
        third = PlayerActivity.objects.create(player=self.player, name="DEEP WORK")

        self.assertEqual(Activity.objects.filter(player=self.player).count(), 1)
        self.assertEqual(first.activity_id, second.activity_id)
        self.assertEqual(first.activity_id, third.activity_id)
        self.assertEqual(first.activity.name, "Deep Work")

    def test_creating_a_session_with_a_new_name_creates_a_new_activity(self):
        PlayerActivity.objects.create(player=self.player, name="Deep Work")
        activity = PlayerActivity.objects.create(player=self.player, name="Admin")

        self.assertEqual(Activity.objects.filter(player=self.player).count(), 2)
        self.assertEqual(activity.activity.name, "Admin")

    def test_blank_named_session_leaves_activity_unset(self):
        activity = PlayerActivity.objects.create(player=self.player, name="")

        self.assertIsNone(activity.activity)

    def test_renaming_a_session_re_resolves_its_activity(self):
        first = PlayerActivity.objects.create(player=self.player, name="Deep Work")
        session = PlayerActivity.objects.create(player=self.player, name="")

        session.rename("deep work")

        self.assertEqual(session.activity_id, first.activity_id)

    def test_activities_are_not_shared_across_players(self):
        other_user = User.objects.create_user(email="other@test.com", password="pass")
        other_player, _ = Player.objects.get_or_create(user=other_user)

        mine = PlayerActivity.objects.create(player=self.player, name="Deep Work")
        theirs = PlayerActivity.objects.create(player=other_player, name="Deep Work")

        self.assertNotEqual(mine.activity_id, theirs.activity_id)
        self.assertEqual(Activity.objects.filter(name__iexact="deep work").count(), 2)
