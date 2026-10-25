import unittest.mock

from django.contrib.gis.geos import Point, Polygon
from django.test import TestCase

from economy import constants
from economy.conversion import convert_goods
from economy.models import GoodsStock
from locations.models import Building, InteriorSpace, PopulationCentre
from locations.constants import PROJECT_SRID


def _square(cx, cy, half_side):
    return Polygon(
        (
            (cx - half_side, cy - half_side),
            (cx - half_side, cy + half_side),
            (cx + half_side, cy + half_side),
            (cx + half_side, cy - half_side),
            (cx - half_side, cy - half_side),
        ),
        srid=PROJECT_SRID,
    )


def _make_building(name, building_type, storage_usage, storage_area, centre):
    building = Building.objects.create(
        name=name,
        building_type=building_type,
        location=Point(0, 0, srid=PROJECT_SRID),
        footprint=_square(0, 0, 5),
        population_centre=centre,
    )
    if storage_area:
        InteriorSpace.objects.create(
            building=building, name="Storage", usage=storage_usage, area=storage_area
        )
    return building


class ConvertGoodsTests(TestCase):
    def setUp(self):
        self.centre = PopulationCentre.objects.create(
            name="Millville",
            location=Point(0, 0, srid=PROJECT_SRID),
            boundary=_square(0, 0, 50),
        )
        self.granary = _make_building(
            "Granary", "granary", "grain_storage", 1000.0, self.centre
        )
        self.mill = _make_building("Mill", "mill", "flour_storage", 1000.0, self.centre)
        GoodsStock.objects.create(
            building=self.granary,
            good_type=GoodsStock.GoodType.WHEAT,
            quantity=500_000.0,
        )

    def test_converts_full_labor_capped_amount_when_unconstrained(self):
        converted = convert_goods(
            self.granary,
            self.mill,
            input_good=GoodsStock.GoodType.WHEAT,
            output_good=GoodsStock.GoodType.FLOUR,
            workers_present=2,
            per_worker_capacity=20_000.0,
            conversion_ratio=0.75,
        )

        self.assertEqual(converted, 40_000.0)
        wheat = GoodsStock.objects.get(building=self.granary, good_type="wheat")
        flour = GoodsStock.objects.get(building=self.mill, good_type="flour")
        self.assertEqual(wheat.quantity, 460_000.0)
        self.assertEqual(flour.quantity, 30_000.0)

    def test_capped_by_available_input_stock(self):
        wheat = GoodsStock.objects.get(building=self.granary, good_type="wheat")
        wheat.quantity = 5_000.0
        wheat.save(update_fields=["quantity"])

        converted = convert_goods(
            self.granary,
            self.mill,
            input_good=GoodsStock.GoodType.WHEAT,
            output_good=GoodsStock.GoodType.FLOUR,
            workers_present=10,
            per_worker_capacity=20_000.0,
            conversion_ratio=0.75,
        )

        self.assertEqual(converted, 5_000.0)
        wheat.refresh_from_db()
        self.assertEqual(wheat.quantity, 0.0)

    def test_throttles_input_when_output_storage_would_overflow_instead_of_wasting(
        self,
    ):
        # Tiny flour storage: room for far less flour than the labor-capped
        # 40,000g of wheat would produce at a 0.75 ratio.
        flour_space = InteriorSpace.objects.get(
            building=self.mill, usage="flour_storage"
        )
        # capacity = 0.0075 * STORAGE_CAPACITY_PER_AREA_WEIGHT (1_000_000.0)
        # = 7500.0g
        flour_space.area = 0.0075
        flour_space.save(update_fields=["area"])

        converted = convert_goods(
            self.granary,
            self.mill,
            input_good=GoodsStock.GoodType.WHEAT,
            output_good=GoodsStock.GoodType.FLOUR,
            workers_present=2,
            per_worker_capacity=20_000.0,
            conversion_ratio=0.75,
        )

        # 7500g of flour headroom / 0.75 ratio = 10,000g of wheat, not the
        # full labor-capped 40,000 - and none of the wheat is wasted, it's
        # simply left in the granary.
        self.assertAlmostEqual(converted, 7_500.0 / 0.75)
        wheat = GoodsStock.objects.get(building=self.granary, good_type="wheat")
        flour = GoodsStock.objects.get(building=self.mill, good_type="flour")
        self.assertAlmostEqual(wheat.quantity, 500_000.0 - (7_500.0 / 0.75))
        self.assertEqual(flour.quantity, 7_500.0)

    def test_no_input_stock_converts_nothing(self):
        GoodsStock.objects.filter(building=self.granary, good_type="wheat").delete()

        converted = convert_goods(
            self.granary,
            self.mill,
            input_good=GoodsStock.GoodType.WHEAT,
            output_good=GoodsStock.GoodType.FLOUR,
            workers_present=5,
            per_worker_capacity=20_000.0,
            conversion_ratio=0.75,
        )

        self.assertEqual(converted, 0)
        flour = GoodsStock.objects.filter(building=self.mill, good_type="flour").first()
        self.assertTrue(flour is None or flour.quantity == 0)

    def test_capacity_is_per_good_type_not_shared(self):
        # The mill has a flour_storage interior but no grain_storage one -
        # its wheat capacity should read 0, independent of its flour
        # capacity, since the two usages are tracked separately.
        wheat_stock, _ = GoodsStock.objects.get_or_create(
            building=self.mill, good_type=GoodsStock.GoodType.WHEAT
        )
        flour_stock, _ = GoodsStock.objects.get_or_create(
            building=self.mill, good_type=GoodsStock.GoodType.FLOUR
        )
        self.assertEqual(wheat_stock.capacity, 0)
        self.assertGreater(flour_stock.capacity, 0)


class GoodsStockCapacityUnitKindTests(TestCase):
    """
    GoodsStock.capacity picks its formula per good_type: direct weight-per-
    area for sacked/shelved goods (flour, bread), volume-per-area bridged
    through a bulk density for loose bulk goods (wheat), and direct
    volume-per-area for a genuinely volume-accounted good (no such good
    exists yet, exercised here via a monkeypatched mapping).
    """

    def setUp(self):
        self.centre = PopulationCentre.objects.create(
            name="Storeville",
            location=Point(0, 0, srid=PROJECT_SRID),
            boundary=_square(0, 0, 50),
        )

    def test_wheat_capacity_uses_bulk_density_not_flat_weight_constant(self):
        granary = _make_building(
            "Granary", "granary", "grain_storage", 10.0, self.centre
        )
        wheat_stock = GoodsStock.objects.create(
            building=granary, good_type=GoodsStock.GoodType.WHEAT
        )

        # 10.0 m^2 * STORAGE_CAPACITY_PER_AREA_VOLUME (1_000.0 L/m^2) *
        # wheat bulk density (770.0 g/L) = 7_700_000.0g - not
        # 10.0 * STORAGE_CAPACITY_PER_AREA_WEIGHT (1_000_000.0) = 10_000_000.0g,
        # which is what a flat weight-based good with the same area would get.
        self.assertEqual(wheat_stock.capacity, 10.0 * 1_000.0 * 770.0)

    def test_volume_kind_good_uses_direct_volume_capacity_with_no_density(self):
        # No real volume-accounted good exists yet, so this proves the
        # capacity property's direct-VOLUME branch by wiring a temporary
        # good into GOOD_TYPE_UNIT for the duration of the test.
        # GOOD_TYPE_UNIT is imported by reference into economy.models, so
        # patching the dict here (same object) is visible there too.
        building = _make_building("Cellar", "granary", "storage", 4.0, self.centre)
        stock = GoodsStock.objects.create(building=building, good_type="ale")

        with unittest.mock.patch.dict(
            constants.GOOD_TYPE_UNIT, {"ale": constants.UnitKind.VOLUME}
        ):
            # 4.0 m^2 * STORAGE_CAPACITY_PER_AREA_VOLUME (1_000.0 L/m^2), no
            # density multiplier since "ale" isn't in GOOD_TYPE_BULK_DENSITY.
            self.assertEqual(stock.capacity, 4.0 * 1_000.0)
