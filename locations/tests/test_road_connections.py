from django.contrib.gis.geos import LineString, Point
from django.test import TestCase

from locations.models import PopulationCentre, Road
from locations.services.road_connections import connect_nearest_village_roads


def _centre(name: str, x: float, y: float) -> PopulationCentre:
    return PopulationCentre.objects.create(name=name, location=Point(x, y, srid=3857))


class ConnectNearestVillageRoadsTest(TestCase):
    def test_connects_closest_endpoints_between_two_villages(self):
        near = _centre("Near", 0, 0)
        Road.objects.create(
            population_centre=near,
            geom=LineString((0, 0), (10, 0), srid=3857),
        )
        far = _centre("Far", 1000, 0)
        Road.objects.create(
            population_centre=far,
            geom=LineString((990, 0), (1000, 0), srid=3857),
        )
        # A third, more distant village whose closer road endpoint should be
        # ignored in favour of "far"'s nearer one.
        farther = _centre("Farther", 5000, 0)
        Road.objects.create(
            population_centre=farther,
            geom=LineString((4000, 0), (4990, 0), srid=3857),
        )

        connector = connect_nearest_village_roads(near)

        self.assertIsNotNone(connector)
        coords = connector.geom.coords
        self.assertEqual(len(coords), 2)
        self.assertIn((10.0, 0.0), coords)
        self.assertIn((990.0, 0.0), coords)

    def test_returns_none_when_village_has_no_roads(self):
        empty = _centre("Empty", 0, 0)
        _centre("Other", 100, 0)

        self.assertIsNone(connect_nearest_village_roads(empty))

    def test_returns_none_when_no_other_village_has_roads(self):
        solo = _centre("Solo", 0, 0)
        Road.objects.create(
            population_centre=solo,
            geom=LineString((0, 0), (10, 0), srid=3857),
        )
        _centre("Roadless", 100, 0)

        self.assertIsNone(connect_nearest_village_roads(solo))
