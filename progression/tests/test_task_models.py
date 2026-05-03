from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from progression.models import PlayerActivity, Task


class TaskModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="task-model@example.com",
            password="pass",
        )
        self.player = self.user.player
        self.task = Task.objects.create(
            player=self.player,
            name="Write docs",
        )

    def test_last_worked_on_uses_latest_completed_linked_activity(self):
        older_completed_at = timezone.now() - timedelta(days=3)
        PlayerActivity.objects.create(
            player=self.player,
            name="Older task work",
            task=self.task,
            duration=30,
            is_complete=True,
            completed_at=older_completed_at,
        )

        incomplete_activity = PlayerActivity.objects.create(
            player=self.player,
            name="Incomplete task work",
            task=self.task,
            duration=20,
        )
        PlayerActivity.objects.filter(pk=incomplete_activity.pk).update(
            last_updated=timezone.now(),
        )

        newer_completed_at = timezone.now() - timedelta(hours=2)
        PlayerActivity.objects.create(
            player=self.player,
            name="Newer task work",
            task=self.task,
            duration=45,
            is_complete=True,
            completed_at=newer_completed_at,
        )

        self.assertEqual(self.task.last_worked_on, newer_completed_at)
