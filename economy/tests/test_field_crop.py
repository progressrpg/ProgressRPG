from datetime import timedelta

from django.contrib.gis.geos import Point, Polygon
from django.test import TestCase
from django.utils import timezone

from economy.constants import GROWTH_DURATION
from economy.models import FieldCrop
from locations.models import Building, LandArea, PopulationCentre, Subzone
from locations.constants import PROJECT_SRID

SQUARE = Polygon(((0, 0), (0, 10), (10, 10), (10, 0), (0, 0)), srid=PROJECT_SRID)


class FieldCropGrowthProgressTest(TestCase):
    def setUp(self):
        centre = PopulationCentre.objects.create(
            name="Testville", location=Point(0, 0, srid=PROJECT_SRID)
        )
        land_area = LandArea.objects.create(
            name="Testville Land Area", population_centre=centre, size=1.0
        )
        self.subzone = Subzone.objects.create(
            name="Testville - Crops",
            land_area=land_area,
            usage="crops",
            size=0.6,
            boundary=SQUARE,
        )
        self.shelter = Building.objects.create(
            name="Shelter", building_type="field_shelter"
        )

    def make_crop(self, stage, planted_at=None):
        return FieldCrop.objects.create(
            subzone=self.subzone,
            shelter_building=self.shelter,
            stage=stage,
            planted_at=planted_at,
        )

    def test_fallow_has_no_progress(self):
        crop = self.make_crop(FieldCrop.Stage.FALLOW)
        self.assertIsNone(crop.growth_progress)

    def test_ready_has_no_progress(self):
        crop = self.make_crop(
            FieldCrop.Stage.READY, planted_at=timezone.now() - GROWTH_DURATION
        )
        self.assertIsNone(crop.growth_progress)

    def test_just_planted_is_near_zero(self):
        crop = self.make_crop(FieldCrop.Stage.GROWING, planted_at=timezone.now())
        self.assertAlmostEqual(crop.growth_progress, 0.0, places=2)

    def test_halfway_through_growth_duration(self):
        crop = self.make_crop(
            FieldCrop.Stage.GROWING, planted_at=timezone.now() - GROWTH_DURATION / 2
        )
        self.assertAlmostEqual(crop.growth_progress, 0.5, places=2)

    def test_overdue_progress_is_clamped_to_one(self):
        crop = self.make_crop(
            FieldCrop.Stage.GROWING,
            planted_at=timezone.now() - GROWTH_DURATION - timedelta(days=10),
        )
        self.assertEqual(crop.growth_progress, 1.0)
