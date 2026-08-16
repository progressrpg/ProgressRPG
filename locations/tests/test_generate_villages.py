import random

from django.contrib.gis.geos import Point
from django.core.management import call_command
from django.test import TestCase

from locations.management.commands.generate_villages import (
    BUILDING_ZONES,
    create_building_footprint,
)
from locations.models import PopulationCentre


class BuildingFootprintRotationTest(TestCase):
    def test_rotation_produces_non_axis_aligned_footprint(self):
        footprint = create_building_footprint(
            Point(0, 0, srid=3857),
            min_size=10,
            max_size=10,
            irregularity=0,
            rotation=45,
        )
        coords = footprint.coords[0][:-1]
        xs = {round(x, 6) for x, _ in coords}
        ys = {round(y, 6) for _, y in coords}
        # An unrotated rectangle has exactly 2 distinct x values and 2
        # distinct y values across its 4 corners - a 45deg rotation breaks
        # that.
        self.assertTrue(len(xs) > 2 or len(ys) > 2)

    def test_zero_rotation_keeps_axis_aligned_footprint(self):
        footprint = create_building_footprint(
            Point(0, 0, srid=3857), min_size=10, max_size=10, irregularity=0, rotation=0
        )
        coords = footprint.coords[0][:-1]
        xs = {round(x, 6) for x, _ in coords}
        ys = {round(y, 6) for _, y in coords}
        self.assertEqual(len(xs), 2)
        self.assertEqual(len(ys), 2)


class SpawnVillagesZoneGroupingTest(TestCase):
    def test_same_zone_buildings_cluster_closer_than_different_zone_buildings(self):
        random.seed(42)
        call_command("generate_villages", num_centres=1, grid_size=5000, min_distance=3)

        centre = PopulationCentre.objects.get()
        buildings = list(centre.buildings.all())
        self.assertGreater(len(buildings), 1)

        def zone_of(building):
            return BUILDING_ZONES.get(building.building_type, "social")

        same_zone_distances = []
        cross_zone_distances = []
        for i, a in enumerate(buildings):
            for b in buildings[i + 1 :]:
                d = a.location.distance(b.location)
                if zone_of(a) == zone_of(b):
                    same_zone_distances.append(d)
                else:
                    cross_zone_distances.append(d)

        self.assertTrue(same_zone_distances and cross_zone_distances)
        avg_same = sum(same_zone_distances) / len(same_zone_distances)
        avg_cross = sum(cross_zone_distances) / len(cross_zone_distances)
        # Statistical, not exact-position, per issue #656's plan - buildings
        # of the same zone should on average sit closer together than
        # buildings from different zones.
        self.assertLess(avg_same, avg_cross)
