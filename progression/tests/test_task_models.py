from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
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

    def test_due_at_is_optional(self):
        task = Task.objects.create(player=self.player, name="No due date")
        self.assertIsNone(task.due_at)

        due_at = timezone.now() + timedelta(days=1)
        task.due_at = due_at
        task.full_clean()
        task.save()
        task.refresh_from_db()
        self.assertEqual(task.due_at, due_at)

    def test_valid_parent_subtask_assignment(self):
        subtask = Task(player=self.player, name="Subtask", parent=self.task)
        subtask.full_clean()
        subtask.save()

        self.assertEqual(subtask.parent, self.task)
        self.assertIn(subtask, self.task.subtasks.all())

    def test_self_parent_rejected(self):
        self.task.parent = self.task
        with self.assertRaises(ValidationError):
            self.task.clean()

    def test_grandparent_nesting_rejected(self):
        subtask = Task.objects.create(
            player=self.player, name="Subtask", parent=self.task
        )
        grandchild = Task(player=self.player, name="Grandchild", parent=subtask)

        with self.assertRaises(ValidationError):
            grandchild.clean()

    def test_parent_with_subtasks_cannot_get_a_parent(self):
        Task.objects.create(player=self.player, name="Subtask", parent=self.task)
        other = Task.objects.create(player=self.player, name="Other task")

        self.task.parent = other
        with self.assertRaises(ValidationError):
            self.task.clean()

    def test_cross_player_parent_rejected(self):
        other_user = get_user_model().objects.create_user(
            email="other-player@example.com", password="pass"
        )
        other_task = Task.objects.create(player=other_user.player, name="Theirs")

        subtask = Task(player=self.player, name="Subtask", parent=other_task)
        with self.assertRaises(ValidationError):
            subtask.clean()

    def test_cascade_delete_removes_subtasks(self):
        subtask = Task.objects.create(
            player=self.player, name="Subtask", parent=self.task
        )
        subtask_id = subtask.id

        self.task.delete()

        self.assertFalse(Task.objects.filter(pk=subtask_id).exists())

    def test_total_time_rolls_up_subtask_time(self):
        PlayerActivity.objects.create(
            player=self.player,
            name="Parent work",
            task=self.task,
            duration=50,
            is_complete=True,
        )
        subtask = Task.objects.create(
            player=self.player, name="Subtask", parent=self.task
        )
        PlayerActivity.objects.create(
            player=self.player,
            name="Subtask work",
            task=subtask,
            duration=30,
            is_complete=True,
        )

        self.assertEqual(subtask.total_time, 30)
        self.assertEqual(self.task.total_time, 80)

    def test_total_time_with_no_subtasks_unchanged(self):
        PlayerActivity.objects.create(
            player=self.player,
            name="Solo work",
            task=self.task,
            duration=40,
            is_complete=True,
        )

        self.assertEqual(self.task.total_time, 40)
