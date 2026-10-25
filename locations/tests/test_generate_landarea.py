import random

from django.contrib.gis.geos import Point
from django.core.management import call_command
from django.test import TestCase

from locations.management.commands.generate_landarea import CROPS_SUBZONE_FRACTION
from locations.models import LandArea
from locations.tests.factories import make_centre_with_building
from character.models import Character
from locations.constants import PROJECT_SRID


class GenerateLandareaCommandTest(TestCase):
    def setUp(self):
        # Deterministic placement - the command's own randomness (direction/
        # margin) otherwise makes assertions flaky.
        random.seed(1234)

    def test_places_landarea_outside_the_boundary(self):
        centre = make_centre_with_building(
            "Landtest village", Point(0, 0, srid=PROJECT_SRID)
        )
        Character.objects.create(population_centre=centre)
        original_boundary = centre.boundary

        call_command("generate_landarea")

        landarea = LandArea.objects.get(population_centre=centre)
        # A farm's crops allocation is split into 2-3 separate plots (issue
        # #656) rather than a single Subzone.
        self.assertIn(landarea.subzones.filter(usage="crops").count(), (2, 3))

        centre.refresh_from_db()
        # The LandArea is deliberately left outside the village boundary
        # rather than folded into it - the boundary polygon is untouched,
        # and there must be a real gap so it doesn't visually fuse onto the
        # boundary line.
        self.assertFalse(centre.boundary.intersects(landarea.boundary))
        self.assertEqual(centre.boundary.area, original_boundary.area)

    def test_avoids_overlapping_a_neighbouring_villages_boundary(self):
        centre_a = make_centre_with_building(
            "Village A", Point(0, 0, srid=PROJECT_SRID)
        )
        Character.objects.create(population_centre=centre_a)
        centre_b = make_centre_with_building(
            "Village B", Point(500, 0, srid=PROJECT_SRID)
        )
        Character.objects.create(population_centre=centre_b)

        call_command("generate_landarea")

        landarea_a = LandArea.objects.get(population_centre=centre_a)
        landarea_b = LandArea.objects.get(population_centre=centre_b)

        centre_b.refresh_from_db()
        centre_a.refresh_from_db()
        self.assertFalse(centre_b.boundary.intersects(landarea_a.boundary))
        self.assertFalse(centre_a.boundary.intersects(landarea_b.boundary))

    def test_skips_centre_with_no_residents(self):
        make_centre_with_building("Empty village", Point(0, 0, srid=PROJECT_SRID))

        call_command("generate_landarea")

        self.assertEqual(LandArea.objects.count(), 0)

    def test_subzone_boundaries_are_irregular_not_perfect_rectangles(self):
        centre = make_centre_with_building(
            "Irregular village", Point(0, 0, srid=PROJECT_SRID)
        )
        Character.objects.create(population_centre=centre)

        call_command("generate_landarea")

        landarea = LandArea.objects.get(population_centre=centre)
        for subzone in landarea.subzones.all():
            coords = subzone.boundary.coords[0][:-1]  # drop the closing point
            xs = {round(x, 6) for x, _ in coords}
            ys = {round(y, 6) for _, y in coords}
            # A perfect axis-aligned rectangle has exactly 2 distinct x values
            # and 2 distinct y values across its 4 corners - jitter should
            # break that for at least one axis.
            self.assertTrue(
                len(xs) > 2 or len(ys) > 2,
                f"{subzone.usage} subzone boundary looks like an unjittered rectangle: {coords}",
            )

    def test_crops_plots_area_stays_proportionate_to_intended_fraction(self):
        centre = make_centre_with_building(
            "Proportion village", Point(0, 0, srid=PROJECT_SRID)
        )
        Character.objects.create(population_centre=centre)

        call_command("generate_landarea")

        landarea = LandArea.objects.get(population_centre=centre)
        crops_subzones = list(landarea.subzones.filter(usage="crops"))
        total_crops_area = sum(s.boundary.area for s in crops_subzones)
        landarea_area = landarea.boundary.area

        expected_fraction = CROPS_SUBZONE_FRACTION
        actual_fraction = total_crops_area / landarea_area
        # Jitter perturbs each plot's edges by up to FIELD_IRREGULARITY of its
        # own width/height, so the combined area should stay close to (not
        # exactly at) the intended 60% share.
        self.assertAlmostEqual(actual_fraction, expected_fraction, delta=0.1)
