"""API and XP tests for the tasks core loop (issue #467).

Covers:
- ``PlayerActivity.get_xp_reward_summary`` applying the task XP multiplier
- The task list/detail endpoints (ownership scoping, create, filtering)
- The first-completion bonus awarded by ``TaskViewSet.partial_update``
"""

from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import GameSettings
from progression.models import PlayerActivity, Task

from users.tests import user_factory


class TaskXpMultiplierTests(APITestCase):
    """``get_xp_reward_summary`` applies the task multiplier only when linked."""

    def setUp(self):
        self.user = user_factory(with_player=True)
        self.player = self.user.player
        self.task = Task.objects.create(player=self.player, name="Write docs")
        # Pin the relevant GameSettings so the expected numbers are explicit.
        settings = GameSettings.current()
        settings.default_activity_xp_per_second = "1.0000"
        settings.task_activity_xp_multiplier = "1.25"
        settings.save(
            update_fields=[
                "default_activity_xp_per_second",
                "task_activity_xp_multiplier",
            ]
        )

    def test_task_linked_activity_applies_multiplier(self):
        activity = PlayerActivity.objects.create(
            player=self.player, name="Task work", duration=100, task=self.task
        )

        summary = activity.get_xp_reward_summary()

        self.assertEqual(summary["base_xp"], 100)
        self.assertEqual(summary["task_xp_multiplier"], 1.25)
        self.assertEqual(summary["xp_multiplier"], 1.25)
        self.assertEqual(summary["xp_gained"], 125)

    def test_unlinked_activity_does_not_apply_multiplier(self):
        activity = PlayerActivity.objects.create(
            player=self.player, name="Loose work", duration=100
        )

        summary = activity.get_xp_reward_summary()

        # Whole-number multipliers are formatted as ints (see ``_fmt``).
        self.assertEqual(summary["task_xp_multiplier"], 1)
        self.assertEqual(summary["xp_multiplier"], 1)
        self.assertEqual(summary["xp_gained"], 100)


class TaskViewSetTests(APITestCase):
    """CRUD, ownership scoping and filtering on the tasks endpoint."""

    def setUp(self):
        self.user = user_factory(with_player=True)
        self.player = self.user.player
        self.other_user = user_factory(with_player=True)
        self.client.force_authenticate(user=self.user)

    def test_create_assigns_requesting_player(self):
        response = self.client.post(reverse("tasks-list"), {"name": "New task"})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        task = Task.objects.get(pk=response.data["id"])
        self.assertEqual(task.player, self.player)

    def test_list_only_returns_own_tasks(self):
        Task.objects.create(player=self.player, name="Mine")
        Task.objects.create(player=self.other_user.player, name="Theirs")

        response = self.client.get(reverse("tasks-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [t["name"] for t in response.data["results"]]
        self.assertEqual(names, ["Mine"])

    def test_cannot_access_another_players_task(self):
        other_task = Task.objects.create(player=self.other_user.player, name="Theirs")

        response = self.client.get(reverse("tasks-detail", args=[other_task.id]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_filter_by_completion_state(self):
        Task.objects.create(player=self.player, name="Done", is_complete=True)
        Task.objects.create(player=self.player, name="Todo", is_complete=False)

        response = self.client.get(reverse("tasks-list"), {"is_complete": "true"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [t["name"] for t in response.data["results"]]
        self.assertEqual(names, ["Done"])

    def test_create_with_due_at(self):
        due_at = timezone.now() + timedelta(days=2)
        response = self.client.post(
            reverse("tasks-list"), {"name": "Due task", "due_at": due_at.isoformat()}
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        task = Task.objects.get(pk=response.data["id"])
        self.assertIsNotNone(task.due_at)

    def test_create_subtask_via_parent(self):
        parent = Task.objects.create(player=self.player, name="Parent")

        response = self.client.post(
            reverse("tasks-list"), {"name": "Child", "parent": parent.id}
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        task = Task.objects.get(pk=response.data["id"])
        self.assertEqual(task.parent_id, parent.id)
        self.assertEqual(response.data["subtask_count"], 0)

    def test_reject_subtask_of_subtask(self):
        parent = Task.objects.create(player=self.player, name="Parent")
        child = Task.objects.create(player=self.player, name="Child", parent=parent)

        response = self.client.post(
            reverse("tasks-list"), {"name": "Grandchild", "parent": child.id}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reject_giving_parent_to_task_with_existing_subtasks(self):
        parent = Task.objects.create(player=self.player, name="Parent")
        Task.objects.create(player=self.player, name="Child", parent=parent)
        other = Task.objects.create(player=self.player, name="Other")

        response = self.client.patch(
            reverse("tasks-detail", args=[parent.id]), {"parent": other.id}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_filter_by_parent(self):
        parent = Task.objects.create(player=self.player, name="Parent")
        child = Task.objects.create(player=self.player, name="Child", parent=parent)
        Task.objects.create(player=self.player, name="Unrelated")

        response = self.client.get(reverse("tasks-list"), {"parent": parent.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [t["id"] for t in response.data["results"]]
        self.assertEqual(ids, [child.id])

    def test_filter_by_parent_isnull(self):
        parent = Task.objects.create(player=self.player, name="Parent")
        Task.objects.create(player=self.player, name="Child", parent=parent)

        response = self.client.get(reverse("tasks-list"), {"parent__isnull": "true"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [t["name"] for t in response.data["results"]]
        self.assertEqual(names, ["Parent"])

    def test_filter_by_due_at_range(self):
        in_range = Task.objects.create(
            player=self.player,
            name="In range",
            due_at=timezone.now() + timedelta(days=1),
        )
        Task.objects.create(
            player=self.player,
            name="Out of range",
            due_at=timezone.now() + timedelta(days=10),
        )

        response = self.client.get(
            reverse("tasks-list"),
            {
                "due_at_after": timezone.now().isoformat(),
                "due_at_before": (timezone.now() + timedelta(days=3)).isoformat(),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [t["id"] for t in response.data["results"]]
        self.assertEqual(ids, [in_range.id])

    def test_delete_parent_cascades_via_api(self):
        parent = Task.objects.create(player=self.player, name="Parent")
        child = Task.objects.create(player=self.player, name="Child", parent=parent)

        response = self.client.delete(reverse("tasks-detail", args=[parent.id]))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Task.objects.filter(pk=child.id).exists())

    def test_subtask_count_accuracy(self):
        parent = Task.objects.create(player=self.player, name="Parent")
        Task.objects.create(player=self.player, name="Child 1", parent=parent)
        Task.objects.create(player=self.player, name="Child 2", parent=parent)

        list_response = self.client.get(reverse("tasks-list"))
        detail_response = self.client.get(reverse("tasks-detail", args=[parent.id]))

        parent_in_list = next(
            t for t in list_response.data["results"] if t["id"] == parent.id
        )
        self.assertEqual(parent_in_list["subtask_count"], 2)
        self.assertEqual(detail_response.data["subtask_count"], 2)


class TaskCompletionBonusTests(APITestCase):
    """First mark-complete awards the bonus exactly once (issue #432)."""

    def setUp(self):
        self.user = user_factory(with_player=True)
        self.player = self.user.player
        self.task = Task.objects.create(player=self.player, name="Ship it")
        self.client.force_authenticate(user=self.user)

        settings = GameSettings.current()
        settings.task_completion_xp = 100
        settings.save(update_fields=["task_completion_xp"])

    def _patch(self, **data):
        return self.client.patch(reverse("tasks-detail", args=[self.task.id]), data)

    def test_first_completion_awards_bonus(self):
        response = self._patch(is_complete=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["completion_xp_gained"], 100)
        self.assertIn("level_ups", response.data)

        self.task.refresh_from_db()
        self.assertTrue(self.task.is_complete)
        self.assertIsNotNone(self.task.first_completed_at)

    def test_recompletion_after_undo_awards_no_bonus(self):
        self._patch(is_complete=True)
        first_completed_at = Task.objects.get(pk=self.task.pk).first_completed_at

        undo = self._patch(is_complete=False)
        self.assertEqual(undo.data["completion_xp_gained"], 0)

        recomplete = self._patch(is_complete=True)
        self.assertEqual(recomplete.data["completion_xp_gained"], 0)

        # The original first-completion timestamp is preserved.
        self.task.refresh_from_db()
        self.assertEqual(self.task.first_completed_at, first_completed_at)

    def test_non_completion_update_awards_no_bonus(self):
        response = self._patch(name="Renamed")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["completion_xp_gained"], 0)

        self.task.refresh_from_db()
        self.assertEqual(self.task.name, "Renamed")
        self.assertIsNone(self.task.first_completed_at)
