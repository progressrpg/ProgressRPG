from django.contrib.gis.geos import Point, Polygon
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from character.models import Character, PlayerCharacterLink
from locations.models import PopulationCentre
from users.tests import user_factory


def _boundary(cx, cy, half=50):
    return Polygon(
        (
            (cx - half, cy - half),
            (cx + half, cy - half),
            (cx + half, cy + half),
            (cx - half, cy + half),
            (cx - half, cy - half),
        ),
        srid=3857,
    )


class InitialMapCentreViewTest(TestCase):
    """InitialMapCentreView (`/map/initial-centre/`) picks which village the
    map's camera opens on, and is expected to prefer the requesting player's
    linked character's village over the arbitrary "first" fallback - see the
    view's own docstring."""

    def setUp(self):
        self.first_centre = PopulationCentre.objects.create(
            name="First village",
            location=Point(0, 0, srid=3857),
            boundary=_boundary(0, 0),
        )
        self.linked_centre = PopulationCentre.objects.create(
            name="Linked village",
            location=Point(5000, 5000, srid=3857),
            boundary=_boundary(5000, 5000),
        )
        self.client = APIClient()

    def test_falls_back_to_lowest_pk_centre_with_no_active_link(self):
        user = user_factory(with_player=True)
        self.client.force_authenticate(user=user)

        response = self.client.get(reverse("map-initial-centre"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.first_centre.id)
        self.assertEqual(response.data["name"], self.first_centre.name)
        self.assertEqual(
            list(response.data["bbox"]), list(self.first_centre.boundary.extent)
        )

    def test_prefers_the_active_links_character_population_centre(self):
        user = user_factory(with_player=True)
        character = Character.objects.create(
            given_name="Linked",
            location=Point(5000, 5000, srid=3857),
            population_centre=self.linked_centre,
        )
        PlayerCharacterLink.objects.create(player=user.player, character=character)
        self.client.force_authenticate(user=user)

        response = self.client.get(reverse("map-initial-centre"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.linked_centre.id)
        self.assertEqual(response.data["name"], self.linked_centre.name)
        self.assertEqual(
            list(response.data["bbox"]), list(self.linked_centre.boundary.extent)
        )

    def test_no_boundary_falls_back_to_a_window_around_location(self):
        PopulationCentre.objects.all().delete()
        centre = PopulationCentre.objects.create(
            name="Boundaryless village", location=Point(100, 200, srid=3857)
        )
        user = user_factory(with_player=True)
        self.client.force_authenticate(user=user)

        response = self.client.get(reverse("map-initial-centre"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], centre.id)
        min_x, min_y, max_x, max_y = response.data["bbox"]
        self.assertLess(min_x, 100)
        self.assertGreater(max_x, 100)
        self.assertLess(min_y, 200)
        self.assertGreater(max_y, 200)
