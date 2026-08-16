from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from character.models import Character, RelationshipRole, RelationshipType
from character.services import relationship_services


class MapCharacterDetailViewTest(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            email="detail-viewer@example.com", password="testpassword123"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=user)
        self.character = Character.objects.create(
            given_name="Alice", sex="Female", location=Point(0, 0, srid=3857)
        )
        self.url = reverse("map-character-detail", kwargs={"pk": self.character.id})

    def test_unknown_character_returns_404(self):
        response = self.client.get(
            reverse("map-character-detail", kwargs={"pk": 999999})
        )
        self.assertEqual(response.status_code, 404)

    def test_returns_name_age_sex_and_empty_relationships(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.character.id)
        self.assertEqual(response.data["name"], self.character.name)
        self.assertEqual(response.data["sex"], "Female")
        self.assertIsInstance(response.data["age"], int)
        self.assertEqual(response.data["relationships"], [])

    def test_includes_household_relationships(self):
        husband = Character.objects.create(given_name="Thomas", sex="Male")
        relationship_services.relationship_create(
            RelationshipType.MARRIAGE,
            [
                (self.character, RelationshipRole.SPOUSE),
                (husband, RelationshipRole.SPOUSE),
            ],
        )

        response = self.client.get(self.url)

        self.assertEqual(
            response.data["relationships"],
            [{"character_id": husband.id, "name": "Thomas", "label": "husband"}],
        )
