from django.contrib.gis.geos import Point, Polygon
from django.test import TestCase

from locations.management.commands.generate_paths import Command as GeneratePathsCommand
from locations.models import Node, Path, Building, PopulationCentre
from locations.serializers import PathFeatureSerializer
from locations.constants import PROJECT_SRID


class GeneratePathsRerouteTest(TestCase):
    def test_reroute_paths_around_buildings_inserts_waypoint_when_blocked(self):
        centre = PopulationCentre.objects.create(
            name="Reroute village", location=Point(0, 0, srid=PROJECT_SRID)
        )
        node_a = Node.objects.create(
            name="A",
            location=Point(-20, 0, srid=PROJECT_SRID),
            population_centre=centre,
        )
        node_b = Node.objects.create(
            name="B", location=Point(20, 0, srid=PROJECT_SRID), population_centre=centre
        )
        footprint = Polygon(
            ((-5, -5), (-5, 5), (5, 5), (5, -5), (-5, -5)), srid=PROJECT_SRID
        )
        Building.objects.create(
            name="Blocker",
            building_type="residential",
            location=Point(0, 0, srid=PROJECT_SRID),
            footprint=footprint,
            population_centre=centre,
        )
        path = Path.objects.create(from_node=node_a, to_node=node_b)
        # Sanity check: the straight-line path really does cross the building.
        self.assertTrue(footprint.intersects(path.geom))

        GeneratePathsCommand().reroute_paths_around_buildings([path], centre)

        path.refresh_from_db()
        self.assertEqual(len(path.geom.coords), 3)
        self.assertFalse(footprint.intersects(path.geom))

    def test_reroute_paths_around_buildings_leaves_clear_paths_untouched(self):
        centre = PopulationCentre.objects.create(
            name="Clear village", location=Point(0, 0, srid=PROJECT_SRID)
        )
        node_a = Node.objects.create(
            name="A",
            location=Point(-20, 0, srid=PROJECT_SRID),
            population_centre=centre,
        )
        node_b = Node.objects.create(
            name="B", location=Point(20, 0, srid=PROJECT_SRID), population_centre=centre
        )
        footprint = Polygon(
            ((-5, 50), (-5, 60), (5, 60), (5, 50), (-5, 50)), srid=PROJECT_SRID
        )
        Building.objects.create(
            name="Bystander",
            building_type="residential",
            location=Point(0, 55, srid=PROJECT_SRID),
            footprint=footprint,
            population_centre=centre,
        )
        path = Path.objects.create(from_node=node_a, to_node=node_b)
        original_coords = list(path.geom.coords)

        GeneratePathsCommand().reroute_paths_around_buildings([path], centre)

        path.refresh_from_db()
        self.assertEqual(list(path.geom.coords), original_coords)

    def test_path_feature_serializer_uses_rerouted_geom_not_straight_line(self):
        centre = PopulationCentre.objects.create(
            name="Serializer village", location=Point(0, 0, srid=PROJECT_SRID)
        )
        node_a = Node.objects.create(
            name="A",
            location=Point(-20, 0, srid=PROJECT_SRID),
            population_centre=centre,
        )
        node_b = Node.objects.create(
            name="B", location=Point(20, 0, srid=PROJECT_SRID), population_centre=centre
        )
        footprint = Polygon(
            ((-5, -5), (-5, 5), (5, 5), (5, -5), (-5, -5)), srid=PROJECT_SRID
        )
        Building.objects.create(
            name="Blocker",
            building_type="residential",
            location=Point(0, 0, srid=PROJECT_SRID),
            footprint=footprint,
            population_centre=centre,
        )
        path = Path.objects.create(from_node=node_a, to_node=node_b)
        GeneratePathsCommand().reroute_paths_around_buildings([path], centre)
        path.refresh_from_db()

        feature = PathFeatureSerializer(path).data
        # The serializer must reflect the rerouted 3-point geom, not
        # reconstruct a straight line from from_node/to_node (issue #656 -
        # otherwise the API/map would never show the detour).
        self.assertEqual(len(feature["geometry"]["coordinates"]), 3)
        self.assertEqual(
            feature["geometry"]["coordinates"],
            [[float(x), float(y)] for x, y in path.geom.coords],
        )
