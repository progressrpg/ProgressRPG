from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate

from character.models import PlayerCharacterLink
from progression.views import CharacterActivityViewSet, CharacterQuestViewSet


class CharacterScopedViewSetNoCharacterTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="no-character-viewset@test.com",
            password="test-pass-123",
        )
        self.player = self.user.player
        PlayerCharacterLink.objects.filter(player=self.player, is_active=True).update(
            is_active=False
        )
        self.factory = APIRequestFactory()

    def test_character_activity_list_returns_empty_when_unlinked(self):
        view = CharacterActivityViewSet.as_view({"get": "list"})
        request = self.factory.get("/api/v1/character-activities/")
        force_authenticate(request, user=self.user)

        response = view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])

    def test_character_quest_list_returns_empty_when_unlinked(self):
        view = CharacterQuestViewSet.as_view({"get": "list"})
        request = self.factory.get("/api/v1/character-quests/")
        force_authenticate(request, user=self.user)

        response = view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])
