"""
Tests for the player-activities `submit` action's "latest activities"
response.
"""

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from progression.models import PlayerActivity
from users.tests import user_factory


class SubmitLatestActivitiesTests(APITestCase):
    def setUp(self):
        self.user = user_factory(with_player=True)
        self.player = self.user.player
        self.client.force_authenticate(user=self.user)

    def test_latest_activities_excludes_incomplete_sessions(self):
        # An unrelated active/waiting session sharing today's logical_date -
        # completed_at is still null, so it must not appear in (or bury) the
        # "latest submitted activities" response.
        incomplete = PlayerActivity.objects.create(
            player=self.player, name="Still running", is_complete=False
        )

        to_submit = PlayerActivity.objects.create(
            player=self.player, name="Write tests", duration=30, is_complete=False
        )

        response = self.client.post(
            reverse("playeractivity-submit", args=[to_submit.pk]),
            {"is_complete": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = [a["id"] for a in response.data["activities"]]
        self.assertIn(to_submit.pk, returned_ids)
        self.assertNotIn(incomplete.pk, returned_ids)
