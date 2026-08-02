from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point, Polygon
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from character.models import Character
from ..models import Building, Node, Path, PopulationCentre


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


class MapViewportViewTest(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            email="viewport-viewer@example.com", password="testpassword123"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=user)
        self.url = reverse("map-viewport")

    def test_missing_bbox_returns_400(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 400)

    def test_malformed_bbox_returns_400(self):
        response = self.client.get(self.url, {"bbox": "not,a,valid,bbox"})
        self.assertEqual(response.status_code, 400)

    def test_oversized_bbox_returns_400(self):
        response = self.client.get(self.url, {"bbox": "0,0,1000000,1000000"})
        self.assertEqual(response.status_code, 400)

    def test_empty_viewport_returns_empty_feature_collection(self):
        response = self.client.get(self.url, {"bbox": "-50,-50,50,50"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["features"], [])

    def test_only_villages_overlapping_bbox_are_returned(self):
        PopulationCentre.objects.create(
            name="Near Village",
            location=Point(0, 0, srid=3857),
            boundary=square(0, 0),
        )
        PopulationCentre.objects.create(
            name="Far Village",
            location=Point(5000, 5000, srid=3857),
            boundary=square(5000, 5000),
        )

        response = self.client.get(self.url, {"bbox": "-20,-20,20,20"})

        self.assertEqual(response.status_code, 200)
        boundary_features = [
            f
            for f in response.data["features"]
            if f["properties"].get("feature_type") == "boundary"
        ]
        self.assertEqual(len(boundary_features), 1)
        self.assertEqual(response.data["meta"]["population_centre_count"], 1)

    def test_building_straddling_bbox_edge_is_included(self):
        Building.objects.create(
            name="Edge Building",
            footprint=square(19, 0, half=5),  # spans x=14..24, viewport ends at x=20
        )

        response = self.client.get(self.url, {"bbox": "-20,-20,20,20"})

        self.assertEqual(response.status_code, 200)
        building_features = [
            f
            for f in response.data["features"]
            if f["properties"].get("feature_type") == "building"
        ]
        self.assertEqual(len(building_features), 1)

    def test_character_outside_bbox_is_excluded(self):
        Character.objects.create(name="Faraway", location=Point(9999, 9999, srid=3857))
        Character.objects.create(name="Inside", location=Point(0, 0, srid=3857))

        response = self.client.get(self.url, {"bbox": "-20,-20,20,20"})

        character_features = [
            f
            for f in response.data["features"]
            if f["properties"].get("feature_type") == "character"
        ]
        self.assertEqual(len(character_features), 1)
        self.assertEqual(character_features[0]["properties"]["name"], "Inside")

    def test_cross_village_path_included_when_viewport_is_mid_route(self):
        # Two nodes far apart, both outside a small viewport centred between
        # them - the path's geometry still crosses through the viewport.
        node_a = Node.objects.create(name="A", location=Point(-1000, 0, srid=3857))
        node_b = Node.objects.create(name="B", location=Point(1000, 0, srid=3857))
        Path.objects.create(from_node=node_a, to_node=node_b)

        response = self.client.get(self.url, {"bbox": "-20,-20,20,20"})

        self.assertEqual(response.status_code, 200)
        path_features = [
            f
            for f in response.data["features"]
            if f["properties"].get("feature_type") == "path"
        ]
        self.assertEqual(len(path_features), 1)

    def test_distant_path_not_crossing_viewport_is_excluded(self):
        node_a = Node.objects.create(name="A", location=Point(5000, 5000, srid=3857))
        node_b = Node.objects.create(name="B", location=Point(5100, 5100, srid=3857))
        Path.objects.create(from_node=node_a, to_node=node_b)

        response = self.client.get(self.url, {"bbox": "-20,-20,20,20"})

        path_features = [
            f
            for f in response.data["features"]
            if f["properties"].get("feature_type") == "path"
        ]
        self.assertEqual(path_features, [])
