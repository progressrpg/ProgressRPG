"""
Tests for economy.services.capacity_services - specifically that daily
demand and production capacity are always *derived* from
economy.constants rather than hardcoded, so tuning a constant (e.g.
PER_WORKER_DAILY_BAKING_CAPACITY) automatically flows through to the
population_capacity_report a village-generation rule would read, instead
of silently going stale. Every expected value below is computed from the
same imported constants the service uses, not a literal number - a
constant change should never break these tests, only a change to the
*relationship* between population/workers and demand/capacity should.
"""

import math
from unittest.mock import PropertyMock, patch

from django.contrib.gis.geos import Point
from django.test import TestCase

from character.models import Character
from economy.constants import (
    BREAD_PER_CHARACTER_DAILY_CONSUMPTION,
    FLOUR_TO_BREAD_RATIO,
    LINK_POINTS_PRODUCTIVITY_SCALE,
    MAX_PRODUCTIVITY_BONUS,
    PER_WORKER_DAILY_BAKING_CAPACITY,
    PER_WORKER_DAILY_CAPACITY,
    PER_WORKER_DAILY_MILLING_CAPACITY,
    WHEAT_TO_FLOUR_RATIO,
)
from economy.models import BuildingCapability, FieldCrop
from economy.services.capacity_services import (
    daily_bread_demand,
    daily_flour_demand,
    daily_wheat_demand,
    find_bakery,
    find_granary,
    find_mill,
    population_capacity_report,
    worker_capacity_present,
    workers_present,
)
from locations.models import Building, LandArea, Node, PopulationCentre, Subzone


def _make_centre(name="Testville", resident_count=0):
    """
    Always patches PopulationCentre.resident_count to exactly
    resident_count (including 0) rather than leaving it at the real
    residents.count() when 0 is requested - patch.object patches the
    *class* property, so any test that nests one _make_centre call inside
    another test's still-active patch (e.g. a fresh "empty" centre created
    inside a class whose setUp already patched resident_count for its own
    centre) would otherwise silently inherit the outer patched value
    instead of getting the 0 it asked for.

    Callers must stop the returned patcher themselves via
    self.addCleanup(patcher.stop) - this helper has no access to the
    test's `self`.
    """
    centre = PopulationCentre.objects.create(name=name, location=Point(0, 0, srid=3857))
    patcher = patch.object(
        PopulationCentre,
        "resident_count",
        new_callable=PropertyMock,
        return_value=resident_count,
    )
    patcher.start()
    return centre, patcher


BUILDING_TYPE_TO_ACTIVITY = {"mill": "milling", "bakery": "baking"}


def _make_building(centre, building_type, x):
    building = Building.objects.create(
        name=f"{building_type} at {x}",
        building_type=building_type,
        location=Point(x, 0, srid=3857),
        population_centre=centre,
    )
    activity = BUILDING_TYPE_TO_ACTIVITY.get(building_type)
    if activity:
        BuildingCapability.objects.create(building=building, activity=activity)
    node = Node.objects.create(
        name=f"Node for {building.name}",
        location=building.location,
        kind=Node.Kind.BUILDING,
        building=building,
    )
    return building, node


def _add_workers(building, node, count):
    for i in range(count):
        Character.objects.create(
            given_name=f"Worker{i}",
            location=building.location,
            current_node=node,
            is_moving=False,
        )


def _make_field_crop(centre, shelter, index=0):
    land_area = LandArea.objects.create(
        name=f"{centre.name} Farmland {index}", population_centre=centre, size=1.0
    )
    subzone = Subzone.objects.create(
        land_area=land_area, name=f"{centre.name} Crops {index}", size=1.0
    )
    return FieldCrop.objects.create(subzone=subzone, shelter_building=shelter)


class DailyDemandTests(TestCase):
    """
    daily_bread_demand/daily_flour_demand/daily_wheat_demand for a given
    resident count, checked against the constants/ratios themselves - the
    point is that these relationships hold regardless of what the
    constants are currently tuned to.
    """

    def test_zero_residents_have_zero_demand(self):
        centre, patcher = _make_centre(resident_count=0)
        self.addCleanup(patcher.stop)

        self.assertEqual(daily_bread_demand(centre), 0.0)
        self.assertEqual(daily_flour_demand(centre), 0.0)
        self.assertEqual(daily_wheat_demand(centre), 0.0)

    def test_demand_scales_with_resident_count(self):
        centre, patcher = _make_centre(resident_count=100)
        self.addCleanup(patcher.stop)

        expected_bread = 100 * BREAD_PER_CHARACTER_DAILY_CONSUMPTION
        expected_flour = expected_bread / FLOUR_TO_BREAD_RATIO
        expected_wheat = expected_flour / WHEAT_TO_FLOUR_RATIO

        self.assertEqual(daily_bread_demand(centre), expected_bread)
        self.assertEqual(daily_flour_demand(centre), expected_flour)
        self.assertEqual(daily_wheat_demand(centre), expected_wheat)

    def test_none_population_centre_has_zero_demand(self):
        # find_granary/find_mill/find_bakery all tolerate a None centre
        # (e.g. an orphaned building) - demand should too.
        self.assertEqual(daily_bread_demand(None), 0.0)


class PopulationCapacityReportTests(TestCase):
    """
    population_capacity_report for a village with 100 residents and a
    working bakery/mill/farm staffed by present workers - every expected
    figure below is recomputed from the same constants the report itself
    uses, per this module's docstring.
    """

    def setUp(self):
        self.centre, patcher = _make_centre(name="Capacityville", resident_count=100)
        self.addCleanup(patcher.stop)

        self.bakery, bakery_node = _make_building(self.centre, "bakery", 10)
        _add_workers(self.bakery, bakery_node, count=1)

        self.mill, mill_node = _make_building(self.centre, "mill", 20)
        _add_workers(self.mill, mill_node, count=1)

        self.shelter, shelter_node = _make_building(self.centre, "field_shelter", 30)
        _add_workers(self.shelter, shelter_node, count=1)
        # Two crop plots behind the one shelter - field_count should
        # reflect crop plots, not shelter buildings.
        _make_field_crop(self.centre, self.shelter, index=0)
        _make_field_crop(self.centre, self.shelter, index=1)

    def test_resident_count_and_demand(self):
        report = population_capacity_report(self.centre)

        expected_bread = 100 * BREAD_PER_CHARACTER_DAILY_CONSUMPTION
        expected_flour = expected_bread / FLOUR_TO_BREAD_RATIO
        expected_wheat = expected_flour / WHEAT_TO_FLOUR_RATIO

        self.assertEqual(report.resident_count, 100)
        self.assertEqual(report.daily_bread_demand, expected_bread)
        self.assertEqual(report.daily_flour_demand, expected_flour)
        self.assertEqual(report.daily_wheat_demand, expected_wheat)

    def test_farming_capacity_is_workers_times_harvest_constant(self):
        report = population_capacity_report(self.centre)

        self.assertEqual(report.farming.building_count, 2)  # two FieldCrop plots
        self.assertEqual(report.farming.workers_present, 1)
        self.assertEqual(report.farming.capacity_per_day, 1 * PER_WORKER_DAILY_CAPACITY)
        self.assertEqual(report.farming.demand_per_day, report.daily_wheat_demand)

    def test_milling_capacity_runs_worker_throughput_through_yield_ratio(self):
        report = population_capacity_report(self.centre)

        self.assertEqual(report.milling.building_count, 1)
        self.assertEqual(report.milling.workers_present, 1)
        self.assertEqual(
            report.milling.capacity_per_day,
            1 * PER_WORKER_DAILY_MILLING_CAPACITY * WHEAT_TO_FLOUR_RATIO,
        )
        self.assertEqual(report.milling.demand_per_day, report.daily_flour_demand)

    def test_baking_capacity_runs_worker_throughput_through_yield_ratio(self):
        report = population_capacity_report(self.centre)

        self.assertEqual(report.baking.building_count, 1)
        self.assertEqual(report.baking.workers_present, 1)
        self.assertEqual(
            report.baking.capacity_per_day,
            1 * PER_WORKER_DAILY_BAKING_CAPACITY * FLOUR_TO_BREAD_RATIO,
        )
        self.assertEqual(report.baking.demand_per_day, report.daily_bread_demand)

    def test_understaffed_village_is_reported_as_a_shortfall(self):
        # One worker per role (from setUp) covers 100 residents fine at
        # today's constants - swap in a population large enough that a
        # single worker per role can't possibly keep up, however the
        # constants are tuned, then assert the sign of the comparison
        # rather than a specific magnitude.
        with patch.object(
            PopulationCentre,
            "resident_count",
            new_callable=PropertyMock,
            return_value=1_000_000,
        ):
            report = population_capacity_report(self.centre)

        self.assertTrue(report.baking.is_shortfall)
        self.assertTrue(report.milling.is_shortfall)
        self.assertTrue(report.farming.is_shortfall)
        self.assertLess(report.baking.surplus_per_day, 0)

    def test_fully_staffed_village_is_not_a_shortfall(self):
        # Enough workers at every role to clear 100 residents' demand,
        # computed from the same constants rather than a guessed headcount.
        bread_demand = 100 * BREAD_PER_CHARACTER_DAILY_CONSUMPTION
        flour_demand = bread_demand / FLOUR_TO_BREAD_RATIO
        wheat_demand = flour_demand / WHEAT_TO_FLOUR_RATIO

        bakers_needed = math.ceil(
            bread_demand / (PER_WORKER_DAILY_BAKING_CAPACITY * FLOUR_TO_BREAD_RATIO)
        )
        millers_needed = math.ceil(
            flour_demand / (PER_WORKER_DAILY_MILLING_CAPACITY * WHEAT_TO_FLOUR_RATIO)
        )
        farmers_needed = math.ceil(wheat_demand / PER_WORKER_DAILY_CAPACITY)

        _add_workers(
            self.bakery, Node.objects.get(building=self.bakery), count=bakers_needed
        )
        _add_workers(
            self.mill, Node.objects.get(building=self.mill), count=millers_needed
        )
        _add_workers(
            self.shelter, Node.objects.get(building=self.shelter), count=farmers_needed
        )

        report = population_capacity_report(self.centre)

        self.assertFalse(report.baking.is_shortfall)
        self.assertFalse(report.milling.is_shortfall)
        self.assertFalse(report.farming.is_shortfall)

    def test_village_with_no_buildings_reports_zero_capacity(self):
        centre, patcher = _make_centre(name="Emptyville", resident_count=100)
        self.addCleanup(patcher.stop)

        report = population_capacity_report(centre)

        self.assertEqual(report.baking.building_count, 0)
        self.assertEqual(report.baking.workers_present, 0)
        self.assertEqual(report.baking.capacity_per_day, 0)
        self.assertTrue(report.baking.is_shortfall)

    def test_village_with_no_residents_and_no_buildings_is_not_a_shortfall(self):
        # 0 capacity against 0 demand is a village that hasn't been built
        # out yet, not a shortfall - the zero/zero boundary shouldn't flag
        # red.
        centre, patcher = _make_centre(name="Blankville", resident_count=0)
        self.addCleanup(patcher.stop)

        report = population_capacity_report(centre)

        self.assertEqual(report.daily_bread_demand, 0.0)
        self.assertFalse(report.baking.is_shortfall)


class SharedHelperTests(TestCase):
    """
    workers_present/find_granary/find_mill/find_bakery moved out of
    economy.tasks into this module rather than being duplicated - a
    direct check here, on top of the coverage they already get
    transitively via economy.tests.test_tasks.
    """

    def test_workers_present_excludes_moving_characters(self):
        centre, patcher = _make_centre()
        self.addCleanup(patcher.stop)
        bakery, node = _make_building(centre, "bakery", 10)
        _add_workers(bakery, node, count=2)
        Character.objects.create(
            given_name="EnRoute",
            location=bakery.location,
            current_node=node,
            is_moving=True,
        )

        self.assertEqual(workers_present(bakery), 2)

    def test_find_granary_mill_bakery_return_none_for_empty_centre(self):
        centre, patcher = _make_centre()
        self.addCleanup(patcher.stop)

        self.assertIsNone(find_granary(centre))
        self.assertIsNone(find_mill(centre))
        self.assertIsNone(find_bakery(centre))

    def test_find_granary_mill_bakery_return_none_for_none_centre(self):
        self.assertIsNone(find_granary(None))
        self.assertIsNone(find_mill(None))
        self.assertIsNone(find_bakery(None))


class WorkerCapacityPresentTests(TestCase):
    """
    worker_capacity_present - the link-scaled counterpart to workers_present
    used everywhere a headcount feeds a capacity_per_day labor cap (see
    economy.tasks and population_capacity_report). Expected values are
    derived from LINK_POINTS_PRODUCTIVITY_SCALE/MAX_PRODUCTIVITY_BONUS
    rather than hardcoded, matching this module's "never hardcode" rule.
    """

    def test_zero_iff_workers_present_is_zero(self):
        centre, patcher = _make_centre()
        self.addCleanup(patcher.stop)
        bakery, node = _make_building(centre, "bakery", 10)

        self.assertEqual(worker_capacity_present(bakery), 0)

    def test_unlinked_characters_contribute_exactly_one_each(self):
        centre, patcher = _make_centre()
        self.addCleanup(patcher.stop)
        bakery, node = _make_building(centre, "bakery", 10)
        _add_workers(bakery, node, count=3)

        self.assertEqual(worker_capacity_present(bakery), 3)

    def test_linked_character_contributes_more_than_baseline(self):
        centre, patcher = _make_centre()
        self.addCleanup(patcher.stop)
        bakery, node = _make_building(centre, "bakery", 10)
        Character.objects.create(
            given_name="Linked",
            location=bakery.location,
            current_node=node,
            is_moving=False,
        )
        link_points = LINK_POINTS_PRODUCTIVITY_SCALE / 2

        with patch.object(
            Character,
            "total_link_points",
            new_callable=PropertyMock,
            return_value=link_points,
        ):
            capacity = worker_capacity_present(bakery)

        expected = 1 + (link_points / LINK_POINTS_PRODUCTIVITY_SCALE)
        self.assertEqual(capacity, expected)
        self.assertGreater(capacity, 1)

    def test_productivity_bonus_is_capped_not_unbounded(self):
        centre, patcher = _make_centre()
        self.addCleanup(patcher.stop)
        bakery, node = _make_building(centre, "bakery", 10)
        Character.objects.create(
            given_name="MaxedOut",
            location=bakery.location,
            current_node=node,
            is_moving=False,
        )
        # Vastly more link_points than the scale constant - if the curve
        # were linear rather than capped, this would blow past
        # 1 + MAX_PRODUCTIVITY_BONUS, which is exactly the bug this test
        # guards against (see plan Risk: "unbounded productivity if the
        # curve is implemented as linear by mistake").
        huge_link_points = LINK_POINTS_PRODUCTIVITY_SCALE * 1000

        with patch.object(
            Character,
            "total_link_points",
            new_callable=PropertyMock,
            return_value=huge_link_points,
        ):
            capacity = worker_capacity_present(bakery)

        self.assertEqual(capacity, 1 + MAX_PRODUCTIVITY_BONUS)
