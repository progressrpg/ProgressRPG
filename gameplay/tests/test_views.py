from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from progression.models import Task

User = get_user_model()
from users.tests import user_factory


class LabelActivityViewTests(APITestCase):
    def setUp(self):
        self.user = user_factory(with_player=True)
        self.player = self.user.player
        self.client.force_authenticate(user=self.user)
        self.url = reverse("activitytimer-label-activity")

    def start_timer(self, name="Focus time"):
        timer = self.player.activity_timer
        timer.new_activity(name=name)
        timer.start()
        return timer

    def test_renames_running_activity_without_resetting_progress(self):
        timer = self.start_timer()
        timer.elapsed_time = 42
        timer.save(update_fields=["elapsed_time"])
        original_start_time = timer.start_time

        response = self.client.post(self.url, {"activityName": "Deep work"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        timer.refresh_from_db()
        timer.activity.refresh_from_db()
        self.assertEqual(timer.activity.name, "Deep work")
        self.assertEqual(timer.status, "active")
        self.assertEqual(timer.elapsed_time, 42)
        self.assertEqual(timer.start_time, original_start_time)

    def test_can_clear_the_label_back_to_blank(self):
        self.start_timer(name="Something")

        response = self.client.post(self.url, {"activityName": ""})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        timer = self.player.activity_timer
        timer.activity.refresh_from_db()
        self.assertEqual(timer.activity.name, "")

    def test_attaches_task_alongside_rename(self):
        task = Task.objects.create(player=self.player, name="Ship the feature")
        self.start_timer()

        response = self.client.post(
            self.url, {"activityName": "Ship the feature", "task_id": task.id}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        timer = self.player.activity_timer
        timer.activity.refresh_from_db()
        self.assertEqual(timer.activity.name, "Ship the feature")
        self.assertEqual(timer.activity.task_id, task.id)

    def test_rejects_task_owned_by_another_player(self):
        other_user = user_factory(
            with_player=True, email="otheruser@example.com", password="testpassword123"
        )
        other_task = Task.objects.create(player=other_user.player, name="Not yours")
        self.start_timer()

        response = self.client.post(
            self.url, {"activityName": "Focus time", "task_id": other_task.id}
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_no_op_when_no_timer_is_running(self):
        response = self.client.post(self.url, {"activityName": "Too late"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_op_when_timer_already_completed(self):
        timer = self.start_timer()
        timer.complete()

        response = self.client.post(self.url, {"activityName": "Too late"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(self.url, {"activityName": "Nope"})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class SetActivityGuardTests(APITestCase):
    """
    set_activity() only refused to overwrite a *paused* session holding
    banked time - an active or waiting session (no banked elapsed_time to
    protect) passed the old guard unchecked, and new_activity() would then
    create a replacement activity, orphaning the running one without ever
    completing or discarding it.
    """

    def setUp(self):
        self.user = user_factory(with_player=True)
        self.player = self.user.player
        self.client.force_authenticate(user=self.user)
        self.url = reverse("activitytimer-set-activity")

    def test_refuses_to_overwrite_an_active_session(self):
        timer = self.player.activity_timer
        timer.new_activity(name="First activity", start_immediately=True)
        original_activity_id = timer.activity_id

        response = self.client.post(self.url, {"activityName": "Second activity"})

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["code"], "unresolved_session_pending")
        timer.refresh_from_db()
        self.assertEqual(timer.status, "active")
        self.assertEqual(timer.activity_id, original_activity_id)

    def test_refuses_to_overwrite_a_waiting_session(self):
        timer = self.player.activity_timer
        timer.new_activity(name="First activity")
        original_activity_id = timer.activity_id

        response = self.client.post(self.url, {"activityName": "Second activity"})

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["code"], "unresolved_session_pending")
        timer.refresh_from_db()
        self.assertEqual(timer.status, "waiting")
        self.assertEqual(timer.activity_id, original_activity_id)


class ActivityTimerBroadcastTests(APITestCase):
    """
    Every mutating activity-timer endpoint should push the updated timer to
    the player's other open sessions (tabs/devices) over the `player_{id}`
    WebSocket group, so they can reconcile via loadFromServer instead of
    drifting until their next manual fetch. See issue #759.
    """

    def setUp(self):
        self.user = user_factory(with_player=True)
        self.player = self.user.player
        self.client.force_authenticate(user=self.user)

    def test_set_activity_broadcasts_timer_update(self):
        with patch("gameplay.views.broadcast_activity_timer") as mock_broadcast:
            response = self.client.post(
                reverse("activitytimer-set-activity"), {"activityName": "Focus time"}
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_broadcast.assert_called_once_with(self.player.activity_timer)

    def test_start_broadcasts_timer_update(self):
        self.player.activity_timer.new_activity(name="Focus time")

        with patch("gameplay.views.broadcast_activity_timer") as mock_broadcast:
            response = self.client.post(reverse("activitytimer-start"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_broadcast.assert_called_once_with(self.player.activity_timer)

    def test_label_activity_broadcasts_timer_update(self):
        timer = self.player.activity_timer
        timer.new_activity(name="Focus time")
        timer.start()

        with patch("gameplay.views.broadcast_activity_timer") as mock_broadcast:
            response = self.client.post(
                reverse("activitytimer-label-activity"), {"activityName": "Deep work"}
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_broadcast.assert_called_once_with(timer)

    def test_complete_broadcasts_timer_update(self):
        timer = self.player.activity_timer
        timer.new_activity(name="Focus time")
        timer.start()

        with patch("gameplay.views.broadcast_activity_timer") as mock_broadcast:
            response = self.client.post(
                reverse("activitytimer-complete"),
                {"activityName": "Focus time", "elapsedSeconds": 30},
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_broadcast.assert_called_once_with(timer)
