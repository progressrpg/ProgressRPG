from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from progression.models import PlayerActivity, Project, Task
from users.models import TutorialStep


class SeedPlaywrightUserCommandTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()

    def test_command_creates_a_ready_to_use_playwright_user(self):
        TutorialStep.objects.create(title="Welcome", body="Body", order=1)

        stdout = StringIO()
        call_command(
            "seed_playwright_user",
            email="playwright-command@example.com",
            password="correcthorsebatterystaple",
            stdout=stdout,
        )

        user = self.user_model.objects.get(email="playwright-command@example.com")

        self.assertTrue(user.check_password("correcthorsebatterystaple"))
        self.assertTrue(user.is_confirmed)
        self.assertEqual(str(user.timezone), "UTC")

        player = user.player
        self.assertEqual(player.name, "Playwright Hero")
        self.assertEqual(player.onboarding_step, 2)
        self.assertTrue(player.onboarding_completed)
        self.assertFalse(player.is_deleted)
        self.assertEqual(
            player.tutorial_steps_seen.count(), TutorialStep.objects.count()
        )
        self.assertEqual(player.activity_timer.status, "empty")
        self.assertIsNone(player.activity_timer.activity)

        self.assertIn("Playwright user ready", stdout.getvalue())

    def test_command_resets_existing_playwright_user_state(self):
        TutorialStep.objects.create(title="Welcome", body="Body", order=1)

        user = self.user_model.objects.create_user(
            email="playwright-existing@example.com",
            password="old-password",
        )
        user.is_confirmed = False
        user.timezone = "Europe/Paris"
        user.save(update_fields=["is_confirmed", "timezone"])

        player = user.player
        player.name = "Needs Reset"
        player.onboarding_step = 0
        player.onboarding_completed = False
        player.is_deleted = True
        player.bio = "stale bio"
        player.xp = 99
        player.level = 3
        player.xp_next_level = 250
        player.xp_modifier = 2
        player.save(
            update_fields=[
                "name",
                "onboarding_step",
                "onboarding_completed",
                "is_deleted",
                "bio",
                "xp",
                "level",
                "xp_next_level",
                "xp_modifier",
            ]
        )

        project = Project.objects.create(player=player, name="Stale project")
        task = Task.objects.create(player=player, name="Stale task", project=project)
        PlayerActivity.objects.create(
            player=player,
            name="Stale activity",
            task=task,
        )
        PlayerActivity.objects.create(
            player=player,
            name="Second stale activity",
            project=project,
        )
        player.activity_timer.new_activity("Timer activity")

        call_command(
            "seed_playwright_user",
            email=user.email,
            password="new-password",
            player_name="Stable Hero",
        )

        user.refresh_from_db()
        player.refresh_from_db()
        player.activity_timer.refresh_from_db()

        self.assertTrue(user.check_password("new-password"))
        self.assertTrue(user.is_confirmed)
        self.assertEqual(str(user.timezone), "UTC")

        self.assertEqual(player.name, "Stable Hero")
        self.assertEqual(player.onboarding_step, 2)
        self.assertTrue(player.onboarding_completed)
        self.assertFalse(player.is_deleted)
        self.assertEqual(player.bio, "")
        self.assertEqual(player.xp, 0)
        self.assertEqual(player.level, 0)
        self.assertEqual(player.xp_next_level, 100)
        self.assertEqual(player.xp_modifier, 1)
        self.assertEqual(player.projects.count(), 0)
        self.assertEqual(player.tasks.count(), 0)
        self.assertEqual(player.activities.count(), 0)
        self.assertEqual(player.activity_timer.status, "empty")
        self.assertIsNone(player.activity_timer.activity)
