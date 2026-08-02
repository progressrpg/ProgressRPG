from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point, Polygon
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from ..models import PopulationCentre
from ..utils import WORLD_BOUNDS_PADDING_M


def square(cx, cy, half=5):
    return Polygon(
        (
            (cx - half, cy - half),
            (cx - half, cy + half),
            (cx + half, cy + half),
            (cx + half, cy - half),
            (cx - half, cy - half),
        ),
        srid=3857,
    )


class MapWorldBoundsViewTest(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            email="world-bounds-viewer@example.com", password="testpassword123"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=user)
        self.url = reverse("map-world-bounds")

    def test_no_population_centres_returns_null_bbox(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["bbox"])

    def test_bbox_covers_every_population_centre_with_padding(self):
        PopulationCentre.objects.create(
            name="Near Village",
            location=Point(0, 0, srid=3857),
            boundary=square(0, 0, half=10),
        )
        PopulationCentre.objects.create(
            name="Far Village",
            location=Point(5000, 5000, srid=3857),
            boundary=square(5000, 5000, half=10),
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        min_x, min_y, max_x, max_y = response.data["bbox"]
        self.assertEqual(min_x, 0 - 10 - WORLD_BOUNDS_PADDING_M)
        self.assertEqual(min_y, 0 - 10 - WORLD_BOUNDS_PADDING_M)
        self.assertEqual(max_x, 5000 + 10 + WORLD_BOUNDS_PADDING_M)
        self.assertEqual(max_y, 5000 + 10 + WORLD_BOUNDS_PADDING_M)

    def test_population_centre_without_boundary_falls_back_to_location(self):
        PopulationCentre.objects.create(
            name="Boundaryless Village",
            location=Point(100, 200, srid=3857),
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        min_x, min_y, max_x, max_y = response.data["bbox"]
        self.assertEqual(min_x, 100 - WORLD_BOUNDS_PADDING_M)
        self.assertEqual(min_y, 200 - WORLD_BOUNDS_PADDING_M)
        self.assertEqual(max_x, 100 + WORLD_BOUNDS_PADDING_M)
        self.assertEqual(max_y, 200 + WORLD_BOUNDS_PADDING_M)
