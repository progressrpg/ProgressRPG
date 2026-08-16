from datetime import date, datetime, timedelta
from unittest.mock import PropertyMock, patch

from django.contrib.gis.geos import Point, Polygon
from django.test import TestCase
from django.utils import timezone

from character.models import Character, CharacterLocation
from economy.constants import (
    BREAD_PER_CHARACTER_DAILY_CONSUMPTION,
    FLOUR_TO_BREAD_RATIO,
    GROWTH_DURATION,
    HUNGER_MAX,
    HUNGER_PER_MISSED_MEAL,
    PER_WORKER_DAILY_BAKING_CAPACITY,
    PER_WORKER_DAILY_CAPACITY,
    PER_WORKER_DAILY_MILLING_CAPACITY,
    WHEAT_TO_FLOUR_RATIO,
    YIELD_PER_AREA,
)
from economy.models import (
    BuildingCapability,
    FieldCrop,
    GoodsConversionState,
    GoodsStock,
)
from economy.tasks import (
    advance_bakery_economy_tick,
    advance_bread_consumption_tick,
    advance_field_economy_tick,
    advance_mill_economy_tick,
)
from locations.models import (
    Building,
    InteriorSpace,
    LandArea,
    Node,
    PopulationCentre,
    Subzone,
)

# Fixed reference dates so tests don't depend on the real wall-clock date
# falling inside/outside the sowing window.
IN_WINDOW_DATE = date(2026, 3, 15)
IN_WINDOW_NOW = timezone.make_aware(datetime(2026, 3, 15, 12, 0, 0))
OUT_OF_WINDOW_DATE = date(2026, 8, 1)
OUT_OF_WINDOW_NOW = timezone.make_aware(datetime(2026, 8, 1, 12, 0, 0))


def _unlimited_demand():
    """
    Mill/bakery output is now also capped by bread demand (see
    advance_mill_economy_tick/advance_bakery_economy_tick) - tests that
    exist to exercise the *labor* cap need a population large enough that
    demand is never the binding constraint, without bulk-creating hundreds
    of residents just to hit that headroom.
    """
    return patch.object(
        PopulationCentre, "resident_count", new_callable=PropertyMock, return_value=1000
    )


def _square(cx, cy, half_side):
    return Polygon(
        (
            (cx - half_side, cy - half_side),
            (cx - half_side, cy + half_side),
            (cx + half_side, cy + half_side),
            (cx + half_side, cy - half_side),
            (cx - half_side, cy - half_side),
        ),
        srid=3857,
    )


def _make_field_crop(
    centre_name="Cropville", half_side=10, stage=FieldCrop.Stage.FALLOW
):
    centre_point = Point(0, 0, srid=3857)
    centre = PopulationCentre.objects.create(
        name=centre_name, location=centre_point, boundary=_square(0, 0, 50)
    )
    land_area = LandArea.objects.create(
        name=f"{centre_name} Farmland",
        population_centre=centre,
        location=centre_point,
        boundary=_square(100, 0, half_side),
        size=1.0,
    )
    subzone = Subzone.objects.create(
        land_area=land_area,
        name=f"{centre_name} Farmland - Crops",
        usage="crops",
        boundary=_square(100, 0, half_side),
        location=Point(100, 0, srid=3857),
        size=1.0,
    )
    shelter = Building.objects.create(
        name=f"Field Shelter",
        building_type="field_shelter",
        location=Point(90, 0, srid=3857),
        footprint=_square(90, 0, 5),
        population_centre=centre,
    )
    shelter_node = Node.objects.create(
        name=f"Node for {shelter.name}",
        location=shelter.location,
        kind=Node.Kind.BUILDING,
        building=shelter,
    )
    crop = FieldCrop.objects.create(
        subzone=subzone, shelter_building=shelter, stage=stage
    )
    return centre, subzone, shelter, shelter_node, crop


def _make_granary(centre, storage_area=100.0):
    granary = Building.objects.create(
        name=f"Granary",
        building_type="granary",
        location=Point(-90, 0, srid=3857),
        footprint=_square(-90, 0, 5),
        population_centre=centre,
    )
    InteriorSpace.objects.create(
        building=granary, name="Storage", usage="grain_storage", area=storage_area
    )
    return granary


def _make_mill(centre, grain_area=1000.0, flour_area=1000.0):
    mill = Building.objects.create(
        name=f"Mill",
        building_type="mill",
        location=Point(80, 0, srid=3857),
        footprint=_square(80, 0, 5),
        population_centre=centre,
    )
    BuildingCapability.objects.create(building=mill, activity="milling")
    mill_node = Node.objects.create(
        name=f"Node for {mill.name}",
        location=mill.location,
        kind=Node.Kind.BUILDING,
        building=mill,
    )
    if grain_area:
        InteriorSpace.objects.create(
            building=mill, name="Grain store", usage="grain_storage", area=grain_area
        )
    if flour_area:
        InteriorSpace.objects.create(
            building=mill, name="Flour store", usage="flour_storage", area=flour_area
        )
    return mill, mill_node


def _make_bakery(centre, storage_area=1000.0):
    bakery = Building.objects.create(
        name=f"Bakery",
        building_type="bakery",
        location=Point(60, 0, srid=3857),
        footprint=_square(60, 0, 5),
        population_centre=centre,
    )
    BuildingCapability.objects.create(building=bakery, activity="baking")
    bakery_node = Node.objects.create(
        name=f"Node for {bakery.name}",
        location=bakery.location,
        kind=Node.Kind.BUILDING,
        building=bakery,
    )
    if storage_area:
        InteriorSpace.objects.create(
            building=bakery, name="Storage", usage="storage", area=storage_area
        )
    return bakery, bakery_node


def _make_resident(centre, home_building, name, hunger=0.0):
    character = Character.objects.create(
        given_name=name, location=home_building.location
    )
    CharacterLocation.objects.create(
        character=character,
        location=home_building,
        role=CharacterLocation.Role.HOME,
        is_primary=True,
    )
    character.needs.hunger = hunger
    character.needs.save(update_fields=["hunger"])
    return character


class GenerateFieldsEconomyTickTests(TestCase):
    def test_fallow_crop_replants_inside_the_sowing_window(self):
        _, _, _, _, crop = _make_field_crop(stage=FieldCrop.Stage.FALLOW)

        advance_field_economy_tick(today=IN_WINDOW_DATE, now=IN_WINDOW_NOW)

        crop.refresh_from_db()
        self.assertEqual(crop.stage, FieldCrop.Stage.GROWING)
        self.assertEqual(crop.planted_at, IN_WINDOW_NOW)
        self.assertEqual(crop.last_processed_on, IN_WINDOW_DATE)

    def test_fallow_crop_stays_fallow_outside_the_sowing_window(self):
        _, _, _, _, crop = _make_field_crop(stage=FieldCrop.Stage.FALLOW)

        advance_field_economy_tick(today=OUT_OF_WINDOW_DATE, now=OUT_OF_WINDOW_NOW)

        crop.refresh_from_db()
        self.assertEqual(crop.stage, FieldCrop.Stage.FALLOW)
        self.assertIsNone(crop.planted_at)
        # The tick still counts as having processed this crop today, so a
        # second run the same day is still a no-op.
        self.assertEqual(crop.last_processed_on, OUT_OF_WINDOW_DATE)

    def test_growing_crop_becomes_ready_after_growth_duration(self):
        _, subzone, _, _, crop = _make_field_crop(stage=FieldCrop.Stage.GROWING)
        crop.planted_at = IN_WINDOW_NOW - GROWTH_DURATION - timedelta(hours=1)
        crop.save(update_fields=["planted_at"])

        advance_field_economy_tick(today=IN_WINDOW_DATE, now=IN_WINDOW_NOW)

        crop.refresh_from_db()
        self.assertEqual(crop.stage, FieldCrop.Stage.READY)
        self.assertAlmostEqual(crop.ready_yield, subzone.boundary.area * YIELD_PER_AREA)
        self.assertEqual(crop.harvested_amount, 0)

    def test_growing_crop_not_yet_ready_stays_growing(self):
        _, _, _, _, crop = _make_field_crop(stage=FieldCrop.Stage.GROWING)
        crop.planted_at = IN_WINDOW_NOW
        crop.save(update_fields=["planted_at"])

        advance_field_economy_tick(
            today=IN_WINDOW_DATE + timedelta(days=1),
            now=IN_WINDOW_NOW + timedelta(days=1),
        )

        crop.refresh_from_db()
        self.assertEqual(crop.stage, FieldCrop.Stage.GROWING)
        self.assertIsNone(crop.ready_yield)

    def test_harvest_capped_by_workers_present(self):
        centre, _, shelter, shelter_node, crop = _make_field_crop(
            stage=FieldCrop.Stage.READY
        )
        crop.ready_yield = 1_000_000.0
        crop.harvested_amount = 0
        crop.save(update_fields=["ready_yield", "harvested_amount"])
        _make_granary(centre, storage_area=10000.0)

        Character.objects.create(
            given_name="Worker1",
            location=shelter.location,
            current_node=shelter_node,
            is_moving=False,
        )
        Character.objects.create(
            given_name="Worker2",
            location=shelter.location,
            current_node=shelter_node,
            is_moving=False,
        )

        advance_field_economy_tick()

        crop.refresh_from_db()
        self.assertEqual(crop.harvested_amount, 2 * PER_WORKER_DAILY_CAPACITY)
        self.assertEqual(crop.stage, FieldCrop.Stage.READY)

        stock = GoodsStock.objects.get(building__building_type="granary")
        self.assertEqual(stock.quantity, 2 * PER_WORKER_DAILY_CAPACITY)

    def test_harvest_capped_by_remaining_crop_and_transitions_to_fallow(self):
        centre, _, shelter, shelter_node, crop = _make_field_crop(
            stage=FieldCrop.Stage.READY
        )
        crop.ready_yield = 100_000.0
        crop.harvested_amount = 95_000.0
        crop.save(update_fields=["ready_yield", "harvested_amount"])
        _make_granary(centre, storage_area=10000.0)

        for i in range(5):
            Character.objects.create(
                given_name=f"Worker{i}",
                location=shelter.location,
                current_node=shelter_node,
                is_moving=False,
            )

        advance_field_economy_tick()

        crop.refresh_from_db()
        self.assertEqual(crop.harvested_amount, 100_000.0)
        self.assertEqual(crop.stage, FieldCrop.Stage.FALLOW)

        stock = GoodsStock.objects.get(building__building_type="granary")
        self.assertEqual(stock.quantity, 5_000.0)

    def test_deposit_capped_by_granary_capacity(self):
        centre, _, shelter, shelter_node, crop = _make_field_crop(
            stage=FieldCrop.Stage.READY
        )
        crop.ready_yield = 1_000_000.0
        crop.harvested_amount = 0
        crop.save(update_fields=["ready_yield", "harvested_amount"])
        # Tiny storage area -> tiny capacity (0.1 * STORAGE_CAPACITY_PER_AREA_VOLUME
        # (1_000.0) * wheat bulk density (770.0) = 77_000.0g), much less
        # than one worker's daily harvest capacity (100_000.0g).
        granary = _make_granary(centre, storage_area=0.1)

        Character.objects.create(
            given_name="Worker1",
            location=shelter.location,
            current_node=shelter_node,
            is_moving=False,
        )

        advance_field_economy_tick()

        stock = GoodsStock.objects.get(building=granary)
        self.assertEqual(stock.quantity, stock.capacity)
        self.assertLess(stock.quantity, PER_WORKER_DAILY_CAPACITY)

    def test_no_granary_does_not_raise(self):
        centre, _, shelter, shelter_node, crop = _make_field_crop(
            stage=FieldCrop.Stage.READY
        )
        crop.ready_yield = 1_000_000.0
        crop.harvested_amount = 0
        crop.save(update_fields=["ready_yield", "harvested_amount"])

        Character.objects.create(
            given_name="Worker1",
            location=shelter.location,
            current_node=shelter_node,
            is_moving=False,
        )

        advance_field_economy_tick()

        crop.refresh_from_db()
        self.assertEqual(crop.harvested_amount, PER_WORKER_DAILY_CAPACITY)
        self.assertFalse(GoodsStock.objects.exists())

    def test_running_twice_in_the_same_day_only_processes_once(self):
        centre, _, shelter, shelter_node, crop = _make_field_crop(
            stage=FieldCrop.Stage.READY
        )
        crop.ready_yield = 1_000_000.0
        crop.harvested_amount = 0
        crop.save(update_fields=["ready_yield", "harvested_amount"])
        _make_granary(centre, storage_area=10000.0)

        Character.objects.create(
            given_name="Worker1",
            location=shelter.location,
            current_node=shelter_node,
            is_moving=False,
        )

        advance_field_economy_tick()
        advance_field_economy_tick()

        crop.refresh_from_db()
        self.assertEqual(crop.harvested_amount, PER_WORKER_DAILY_CAPACITY)

        stock = GoodsStock.objects.get(building__building_type="granary")
        self.assertEqual(stock.quantity, PER_WORKER_DAILY_CAPACITY)


class AdvanceMillEconomyTickTests(TestCase):
    def _make_centre_with_wheat(self, wheat_quantity=500_000.0, granary_area=10000.0):
        centre_point = Point(0, 0, srid=3857)
        centre = PopulationCentre.objects.create(
            name="Millville", location=centre_point, boundary=_square(0, 0, 50)
        )
        granary = _make_granary(centre, storage_area=granary_area)
        GoodsStock.objects.create(
            building=granary,
            good_type=GoodsStock.GoodType.WHEAT,
            quantity=wheat_quantity,
        )
        return centre, granary

    def test_mill_converts_wheat_to_flour_capped_by_workers_present(self):
        centre, granary = self._make_centre_with_wheat()
        mill, mill_node = _make_mill(centre)

        Character.objects.create(
            given_name="Miller1",
            location=mill.location,
            current_node=mill_node,
            is_moving=False,
        )
        Character.objects.create(
            given_name="Miller2",
            location=mill.location,
            current_node=mill_node,
            is_moving=False,
        )

        with _unlimited_demand():
            advance_mill_economy_tick()

        expected_input = 2 * PER_WORKER_DAILY_MILLING_CAPACITY
        wheat = GoodsStock.objects.get(building=granary, good_type="wheat")
        flour = GoodsStock.objects.get(building=mill, good_type="flour")
        self.assertEqual(wheat.quantity, 500_000.0 - expected_input)
        self.assertEqual(flour.quantity, expected_input * WHEAT_TO_FLOUR_RATIO)

        state = GoodsConversionState.objects.get(building=mill)
        self.assertEqual(state.last_processed_on, timezone.localdate())

    def test_no_granary_does_not_raise(self):
        centre = PopulationCentre.objects.create(
            name="Granaryless village",
            location=Point(0, 0, srid=3857),
            boundary=_square(0, 0, 50),
        )
        mill, mill_node = _make_mill(centre)
        Character.objects.create(
            given_name="Miller1",
            location=mill.location,
            current_node=mill_node,
            is_moving=False,
        )

        advance_mill_economy_tick()

        self.assertFalse(GoodsStock.objects.exists())
        state = GoodsConversionState.objects.get(building=mill)
        self.assertEqual(state.last_processed_on, timezone.localdate())

    def test_running_twice_in_the_same_day_only_processes_once(self):
        centre, granary = self._make_centre_with_wheat()
        mill, mill_node = _make_mill(centre)
        Character.objects.create(
            given_name="Miller1",
            location=mill.location,
            current_node=mill_node,
            is_moving=False,
        )

        with _unlimited_demand():
            advance_mill_economy_tick()
            advance_mill_economy_tick()

        expected_input = PER_WORKER_DAILY_MILLING_CAPACITY
        wheat = GoodsStock.objects.get(building=granary, good_type="wheat")
        self.assertEqual(wheat.quantity, 500_000.0 - expected_input)

    def test_multiple_mills_in_one_centre_are_both_processed(self):
        centre, granary = self._make_centre_with_wheat(wheat_quantity=1_000_000.0)
        mill_a, node_a = _make_mill(centre)
        mill_b_building = Building.objects.create(
            name="Second Mill",
            building_type="mill",
            location=Point(70, 0, srid=3857),
            footprint=_square(70, 0, 5),
            population_centre=centre,
        )
        BuildingCapability.objects.create(building=mill_b_building, activity="milling")
        node_b = Node.objects.create(
            name="Node for Second Mill",
            location=mill_b_building.location,
            kind=Node.Kind.BUILDING,
            building=mill_b_building,
        )
        InteriorSpace.objects.create(
            building=mill_b_building,
            name="Grain store",
            usage="grain_storage",
            area=1000.0,
        )
        InteriorSpace.objects.create(
            building=mill_b_building,
            name="Flour store",
            usage="flour_storage",
            area=1000.0,
        )

        Character.objects.create(
            given_name="MillerA",
            location=mill_a.location,
            current_node=node_a,
            is_moving=False,
        )
        Character.objects.create(
            given_name="MillerB",
            location=mill_b_building.location,
            current_node=node_b,
            is_moving=False,
        )

        with _unlimited_demand():
            advance_mill_economy_tick()

        self.assertTrue(
            GoodsStock.objects.filter(
                building=mill_a, good_type="flour", quantity__gt=0
            ).exists()
        )
        self.assertTrue(
            GoodsStock.objects.filter(
                building=mill_b_building, good_type="flour", quantity__gt=0
            ).exists()
        )


class AdvanceBakeryEconomyTickTests(TestCase):
    def _make_centre_with_flour(self, flour_quantity=500_000.0):
        centre_point = Point(0, 0, srid=3857)
        centre = PopulationCentre.objects.create(
            name="Bakeville", location=centre_point, boundary=_square(0, 0, 50)
        )
        mill, mill_node = _make_mill(centre)
        GoodsStock.objects.create(
            building=mill,
            good_type=GoodsStock.GoodType.FLOUR,
            quantity=flour_quantity,
        )
        return centre, mill

    def test_bakery_converts_flour_to_bread_capped_by_workers_present(self):
        centre, mill = self._make_centre_with_flour()
        bakery, bakery_node = _make_bakery(centre)

        Character.objects.create(
            given_name="Baker1",
            location=bakery.location,
            current_node=bakery_node,
            is_moving=False,
        )
        Character.objects.create(
            given_name="Baker2",
            location=bakery.location,
            current_node=bakery_node,
            is_moving=False,
        )

        with _unlimited_demand():
            advance_bakery_economy_tick()

        expected_input = 2 * PER_WORKER_DAILY_BAKING_CAPACITY
        flour = GoodsStock.objects.get(building=mill, good_type="flour")
        bread = GoodsStock.objects.get(building=bakery, good_type="bread")
        self.assertEqual(flour.quantity, 500_000.0 - expected_input)
        self.assertEqual(bread.quantity, expected_input * FLOUR_TO_BREAD_RATIO)

        state = GoodsConversionState.objects.get(building=bakery)
        self.assertEqual(state.last_processed_on, timezone.localdate())

    def test_no_mill_does_not_raise(self):
        centre = PopulationCentre.objects.create(
            name="Millless village",
            location=Point(0, 0, srid=3857),
            boundary=_square(0, 0, 50),
        )
        bakery, bakery_node = _make_bakery(centre)
        Character.objects.create(
            given_name="Baker1",
            location=bakery.location,
            current_node=bakery_node,
            is_moving=False,
        )

        advance_bakery_economy_tick()

        self.assertFalse(GoodsStock.objects.exists())
        state = GoodsConversionState.objects.get(building=bakery)
        self.assertEqual(state.last_processed_on, timezone.localdate())

    def test_running_twice_in_the_same_day_only_processes_once(self):
        centre, mill = self._make_centre_with_flour()
        bakery, bakery_node = _make_bakery(centre)
        Character.objects.create(
            given_name="Baker1",
            location=bakery.location,
            current_node=bakery_node,
            is_moving=False,
        )

        with _unlimited_demand():
            advance_bakery_economy_tick()
            advance_bakery_economy_tick()

        expected_input = PER_WORKER_DAILY_BAKING_CAPACITY
        flour = GoodsStock.objects.get(building=mill, good_type="flour")
        self.assertEqual(flour.quantity, 500_000.0 - expected_input)

    def test_multiple_bakeries_in_one_centre_are_both_processed(self):
        centre, mill = self._make_centre_with_flour(flour_quantity=1_000_000.0)
        bakery_a, node_a = _make_bakery(centre)
        bakery_b = Building.objects.create(
            name="Second Bakery",
            building_type="bakery",
            location=Point(50, 0, srid=3857),
            footprint=_square(50, 0, 5),
            population_centre=centre,
        )
        BuildingCapability.objects.create(building=bakery_b, activity="baking")
        node_b = Node.objects.create(
            name="Node for Second Bakery",
            location=bakery_b.location,
            kind=Node.Kind.BUILDING,
            building=bakery_b,
        )
        InteriorSpace.objects.create(
            building=bakery_b, name="Storage", usage="storage", area=1000.0
        )

        Character.objects.create(
            given_name="BakerA",
            location=bakery_a.location,
            current_node=node_a,
            is_moving=False,
        )
        Character.objects.create(
            given_name="BakerB",
            location=bakery_b.location,
            current_node=node_b,
            is_moving=False,
        )

        with _unlimited_demand():
            advance_bakery_economy_tick()

        self.assertTrue(
            GoodsStock.objects.filter(
                building=bakery_a, good_type="bread", quantity__gt=0
            ).exists()
        )
        self.assertTrue(
            GoodsStock.objects.filter(
                building=bakery_b, good_type="bread", quantity__gt=0
            ).exists()
        )


class MultiCapabilityBuildingTests(TestCase):
    """
    A building holding more than one capability (e.g. a communal building
    that both mills and bakes) must be ticked for every one of them on the
    same day. Regression coverage for the GoodsConversionState collision
    described in .claude/plans/building-capabilities-plan.md: before
    GoodsConversionState was keyed by (building, activity), the first tick
    to run would mark the building "processed today" and the second would
    silently skip it.
    """

    def test_milling_and_baking_both_run_on_the_same_day_for_one_building(self):
        centre = PopulationCentre.objects.create(
            name="Communalville",
            location=Point(0, 0, srid=3857),
            boundary=_square(0, 0, 50),
        )
        granary = _make_granary(centre)
        GoodsStock.objects.create(
            building=granary,
            good_type=GoodsStock.GoodType.WHEAT,
            quantity=500_000.0,
        )

        communal = Building.objects.create(
            name="Communal Hall",
            building_type="communal",
            location=Point(80, 0, srid=3857),
            footprint=_square(80, 0, 5),
            population_centre=centre,
        )
        BuildingCapability.objects.create(building=communal, activity="milling")
        BuildingCapability.objects.create(building=communal, activity="baking")
        InteriorSpace.objects.create(
            building=communal, name="Flour store", usage="flour_storage", area=1000.0
        )
        InteriorSpace.objects.create(
            building=communal, name="Bread store", usage="storage", area=1000.0
        )
        node = Node.objects.create(
            name="Node for Communal Hall",
            location=communal.location,
            kind=Node.Kind.BUILDING,
            building=communal,
        )
        Character.objects.create(
            given_name="Worker1",
            location=communal.location,
            current_node=node,
            is_moving=False,
        )

        with _unlimited_demand():
            advance_mill_economy_tick()
            advance_bakery_economy_tick()

        # Bread can only exist if baking found flour to consume - and the
        # only source of flour is the same building's milling tick having
        # already run today, so a positive bread quantity is proof both
        # ticks actually ran rather than the second silently no-opping.
        # (Flour itself may end up fully consumed here, since milling and
        # baking share one building with no minimum retention between
        # them - that's expected, not asserted on directly.)
        bread = GoodsStock.objects.get(building=communal, good_type="bread")
        self.assertGreater(bread.quantity, 0)

        milling_state = GoodsConversionState.objects.get(
            building=communal, activity="milling"
        )
        baking_state = GoodsConversionState.objects.get(
            building=communal, activity="baking"
        )
        self.assertEqual(milling_state.last_processed_on, timezone.localdate())
        self.assertEqual(baking_state.last_processed_on, timezone.localdate())


class AdvanceBreadConsumptionTickTests(TestCase):
    def _make_centre_with_home(self, name="Eatville"):
        centre_point = Point(0, 0, srid=3857)
        centre = PopulationCentre.objects.create(
            name=name, location=centre_point, boundary=_square(0, 0, 50)
        )
        home = Building.objects.create(
            name=f"Home of ({name})",
            building_type="residential",
            location=Point(-60, 0, srid=3857),
            footprint=_square(-60, 0, 5),
            population_centre=centre,
        )
        return centre, home

    def test_character_with_bread_available_is_fed_and_hunger_drops(self):
        centre, home = self._make_centre_with_home()
        bakery, _ = _make_bakery(centre)
        GoodsStock.objects.create(
            building=bakery, good_type=GoodsStock.GoodType.BREAD, quantity=1_000.0
        )
        character = _make_resident(centre, home, "Eater1", hunger=5.0)

        advance_bread_consumption_tick()

        bread = GoodsStock.objects.get(building=bakery, good_type="bread")
        self.assertEqual(
            bread.quantity, 1_000.0 - BREAD_PER_CHARACTER_DAILY_CONSUMPTION
        )

        character.needs.refresh_from_db()
        self.assertEqual(character.needs.hunger, max(0.0, 5.0 - HUNGER_PER_MISSED_MEAL))
        self.assertEqual(character.needs.last_fed_on, timezone.localdate())

    def test_no_bakery_increases_hunger(self):
        centre, home = self._make_centre_with_home()
        character = _make_resident(centre, home, "Eater1", hunger=5.0)

        advance_bread_consumption_tick()

        character.needs.refresh_from_db()
        self.assertEqual(character.needs.hunger, 5.0 + HUNGER_PER_MISSED_MEAL)
        self.assertEqual(character.needs.last_fed_on, timezone.localdate())

    def test_empty_bread_stock_increases_hunger(self):
        centre, home = self._make_centre_with_home()
        _make_bakery(centre)
        character = _make_resident(centre, home, "Eater1", hunger=0.0)

        advance_bread_consumption_tick()

        character.needs.refresh_from_db()
        self.assertEqual(character.needs.hunger, HUNGER_PER_MISSED_MEAL)

    def test_hunger_clamped_at_max(self):
        centre, home = self._make_centre_with_home()
        character = _make_resident(centre, home, "Eater1", hunger=HUNGER_MAX - 1)

        advance_bread_consumption_tick()

        character.needs.refresh_from_db()
        self.assertEqual(character.needs.hunger, HUNGER_MAX)

    def test_running_twice_in_the_same_day_only_processes_once(self):
        centre, home = self._make_centre_with_home()
        bakery, _ = _make_bakery(centre)
        GoodsStock.objects.create(
            building=bakery, good_type=GoodsStock.GoodType.BREAD, quantity=1_000.0
        )
        _make_resident(centre, home, "Eater1", hunger=5.0)

        advance_bread_consumption_tick()
        advance_bread_consumption_tick()

        bread = GoodsStock.objects.get(building=bakery, good_type="bread")
        self.assertEqual(
            bread.quantity, 1_000.0 - BREAD_PER_CHARACTER_DAILY_CONSUMPTION
        )

    def test_two_characters_share_bakery_stock_first_come_first_served(self):
        centre, home = self._make_centre_with_home()
        bakery, _ = _make_bakery(centre)
        GoodsStock.objects.create(
            building=bakery,
            good_type=GoodsStock.GoodType.BREAD,
            quantity=BREAD_PER_CHARACTER_DAILY_CONSUMPTION,
        )
        first = _make_resident(centre, home, "Eater1", hunger=0.0)
        second = _make_resident(centre, home, "Eater2", hunger=0.0)

        advance_bread_consumption_tick()

        bread = GoodsStock.objects.get(building=bakery, good_type="bread")
        self.assertEqual(bread.quantity, 0.0)

        first.needs.refresh_from_db()
        second.needs.refresh_from_db()
        self.assertEqual(first.needs.hunger, 0.0)
        self.assertEqual(second.needs.hunger, HUNGER_PER_MISSED_MEAL)
