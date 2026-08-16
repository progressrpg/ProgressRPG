import random

from django.contrib.gis.geos import Point, Polygon
from django.core.management import call_command
from django.test import TestCase

from locations.management.commands.generate_fields import SHELTER_MIN_SPACING
from locations.management.commands.generate_villages import create_building_footprint
from locations.models import Node, Building, LandArea, Subzone
from locations.tests.factories import make_centre_with_building
from economy.models import FieldCrop


class GenerateFieldsCommandTest(TestCase):
    def setUp(self):
        # Deterministic placement - generate_landarea's own randomness
        # (direction/margin) otherwise makes assertions flaky.
        random.seed(1234)

    def _make_crops_subzone(self, centre, subzone_point):
        """A crops Subzone with real geometry, as generate_landarea would produce."""
        land_area = LandArea.objects.create(
            name=f"{centre.name} Farmland",
            population_centre=centre,
            location=subzone_point,
            boundary=create_building_footprint(subzone_point),
            size=1.0,
        )
        return Subzone.objects.create(
            land_area=land_area,
            name=f"{centre.name} Farmland - Crops",
            usage="crops",
            boundary=create_building_footprint(subzone_point),
            location=subzone_point,
            size=1.0,
        )

    def test_attaches_shelter_and_fieldcrop_to_existing_crops_subzone(self):
        centre = make_centre_with_building("Fieldtest village", Point(0, 0, srid=3857))
        subzone = self._make_crops_subzone(centre, Point(100, 100, srid=3857))

        call_command("generate_fields")

        shelter = Building.objects.get(
            building_type="field_shelter", population_centre=centre
        )
        self.assertTrue(shelter.nodes.filter(kind=Node.Kind.BUILDING_ENTRANCE).exists())
        self.assertTrue(shelter.nodes.filter(kind=Node.Kind.BUILDING).exists())
        # The shelter is house-scale, much smaller than the crop area it sits
        # beside.
        self.assertLess(shelter.footprint.area, subzone.boundary.area)

        crop = FieldCrop.objects.get(subzone=subzone)
        self.assertEqual(crop.shelter_building, shelter)
        self.assertEqual(crop.stage, FieldCrop.Stage.FALLOW)

    def test_skips_crops_subzone_that_already_has_a_fieldcrop(self):
        centre = make_centre_with_building(
            "Already fielded village", Point(0, 0, srid=3857)
        )
        subzone = self._make_crops_subzone(centre, Point(100, 100, srid=3857))
        existing_shelter = Building.objects.create(
            name="Existing shelter",
            building_type="field_shelter",
            location=Point(100, 100, srid=3857),
            footprint=create_building_footprint(Point(100, 100, srid=3857)),
            population_centre=centre,
        )
        FieldCrop.objects.create(
            subzone=subzone,
            shelter_building=existing_shelter,
            stage=FieldCrop.Stage.GROWING,
        )

        call_command("generate_fields")

        self.assertEqual(FieldCrop.objects.filter(subzone=subzone).count(), 1)
        self.assertEqual(
            Building.objects.filter(
                building_type="field_shelter", population_centre=centre
            ).count(),
            1,
        )

    def test_does_nothing_when_no_crops_subzones_exist(self):
        make_centre_with_building("No fields village", Point(0, 0, srid=3857))

        call_command("generate_fields")

        self.assertEqual(FieldCrop.objects.count(), 0)

    def test_multiple_crops_subzones_share_one_shelter(self):
        centre = make_centre_with_building("Multiplot village", Point(0, 0, srid=3857))
        subzone_1 = self._make_crops_subzone(centre, Point(100, 100, srid=3857))
        subzone_2 = self._make_crops_subzone(centre, Point(120, 100, srid=3857))

        call_command("generate_fields")

        shelters = Building.objects.filter(
            building_type="field_shelter", population_centre=centre
        )
        self.assertEqual(shelters.count(), 1)
        shelter = shelters.first()

        crop_1 = FieldCrop.objects.get(subzone=subzone_1)
        crop_2 = FieldCrop.objects.get(subzone=subzone_2)
        self.assertEqual(crop_1.shelter_building, shelter)
        self.assertEqual(crop_2.shelter_building, shelter)

    def test_shelter_placed_on_boundary_vertex_closest_to_village(self):
        centre = make_centre_with_building("Nearside village", Point(0, 0, srid=3857))
        boundary = Polygon(((90, 0), (90, 10), (100, 10), (100, 0), (90, 0)), srid=3857)
        land_area = LandArea.objects.create(
            name=f"{centre.name} Farmland",
            population_centre=centre,
            location=Point(95, 5, srid=3857),
            boundary=boundary,
            size=1.0,
        )
        subzone = Subzone.objects.create(
            land_area=land_area,
            name=f"{centre.name} Farmland - Crops",
            usage="crops",
            boundary=boundary,
            location=Point(95, 5, srid=3857),
            size=1.0,
        )

        call_command("generate_fields")

        shelter = Building.objects.get(
            building_type="field_shelter", population_centre=centre
        )
        # (90, 0) is the boundary vertex closest to the village centre at
        # (0, 0) - with no other shelters yet placed, the shelter should
        # land exactly there (no spacing jitter needed).
        self.assertAlmostEqual(shelter.location.x, 90, places=6)
        self.assertAlmostEqual(shelter.location.y, 0, places=6)

    def test_shelter_placement_respects_minimum_spacing_between_farms(self):
        centre_a = make_centre_with_building("Farm A village", Point(0, 0, srid=3857))
        centre_b = make_centre_with_building("Farm B village", Point(0, 1, srid=3857))

        # Both farms share the exact same field geometry, so their nearest
        # boundary vertex to their own village centre is identical - forcing
        # the second farm's shelter to jitter away to satisfy min spacing.
        boundary = Polygon(((90, 0), (90, 10), (100, 10), (100, 0), (90, 0)), srid=3857)
        for centre in (centre_a, centre_b):
            land_area = LandArea.objects.create(
                name=f"{centre.name} Farmland",
                population_centre=centre,
                location=Point(95, 5, srid=3857),
                boundary=boundary,
                size=1.0,
            )
            Subzone.objects.create(
                land_area=land_area,
                name=f"{centre.name} Farmland - Crops",
                usage="crops",
                boundary=boundary,
                location=Point(95, 5, srid=3857),
                size=1.0,
            )

        call_command("generate_fields")

        shelter_a = Building.objects.get(
            building_type="field_shelter", population_centre=centre_a
        )
        shelter_b = Building.objects.get(
            building_type="field_shelter", population_centre=centre_b
        )
        self.assertGreaterEqual(
            shelter_a.location.distance(shelter_b.location), SHELTER_MIN_SPACING
        )
