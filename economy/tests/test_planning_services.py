"""
Tests for economy.services.planning_services - specifically that
recommended workforce/infrastructure figures are always *derived* from
economy.constants rather than hardcoded, mirroring
test_capacity_services.py's own docstring rationale: tuning a constant
(e.g. PER_WORKER_DAILY_BAKING_CAPACITY) should automatically flow through
to the recommended plan, never silently go stale. Every expected value
below is computed from the same imported constants the service uses.
"""

import math
from unittest.mock import PropertyMock, patch

from django.contrib.gis.geos import Point
from django.test import SimpleTestCase, TestCase

from economy.constants import (
    BREAD_PER_CHARACTER_DAILY_CONSUMPTION,
    FLOUR_TO_BREAD_RATIO,
    PER_WORKER_DAILY_BAKING_CAPACITY,
    PER_WORKER_DAILY_CAPACITY,
    PER_WORKER_DAILY_MILLING_CAPACITY,
    WHEAT_TO_FLOUR_RATIO,
)
from economy.services.planning_services import settlement_plan
from locations.models import PopulationCentre


def _expected_demand(resident_count):
    bread = resident_count * BREAD_PER_CHARACTER_DAILY_CONSUMPTION
    flour = bread / FLOUR_TO_BREAD_RATIO
    wheat = flour / WHEAT_TO_FLOUR_RATIO
    return bread, flour, wheat


def _expected_workers(demand, per_worker_capacity, yield_ratio=1.0):
    if demand <= 0:
        return 0
    return math.ceil(demand / (per_worker_capacity * yield_ratio))


class SettlementPlanFromPopulationTests(SimpleTestCase):
    """
    settlement_plan(population=N) needs no database - it's pure arithmetic
    over a raw resident count.
    """

    def _assert_plan_matches_population(self, resident_count):
        plan = settlement_plan(population=resident_count)

        expected_bread, expected_flour, expected_wheat = _expected_demand(
            resident_count
        )
        self.assertEqual(plan.resident_count, resident_count)
        self.assertEqual(plan.daily_bread_demand, expected_bread)
        self.assertEqual(plan.daily_flour_demand, expected_flour)
        self.assertEqual(plan.daily_wheat_demand, expected_wheat)

        expected_farmers = _expected_workers(expected_wheat, PER_WORKER_DAILY_CAPACITY)
        expected_millers = _expected_workers(
            expected_flour, PER_WORKER_DAILY_MILLING_CAPACITY, WHEAT_TO_FLOUR_RATIO
        )
        expected_bakers = _expected_workers(
            expected_bread, PER_WORKER_DAILY_BAKING_CAPACITY, FLOUR_TO_BREAD_RATIO
        )

        self.assertEqual(plan.farming.workers_needed, expected_farmers)
        self.assertEqual(plan.milling.workers_needed, expected_millers)
        self.assertEqual(plan.baking.workers_needed, expected_bakers)

        self.assertEqual(plan.farming.building_type, "field_shelter")
        self.assertEqual(plan.milling.building_type, "mill")
        self.assertEqual(plan.baking.building_type, "bakery")

        return plan

    def test_zero_population_has_zero_demand_and_workforce(self):
        plan = self._assert_plan_matches_population(0)

        self.assertEqual(plan.farming.workers_needed, 0)
        self.assertEqual(plan.milling.workers_needed, 0)
        self.assertEqual(plan.baking.workers_needed, 0)

    def test_small_settlement(self):
        self._assert_plan_matches_population(1)

    def test_medium_settlement(self):
        self._assert_plan_matches_population(75)

    def test_large_settlement(self):
        self._assert_plan_matches_population(5000)

    def test_milling_and_baking_and_granaries_always_recommended_even_at_zero_population(
        self,
    ):
        # "assume every population centre should have grain storage,
        # milling, and baking even if these are small" - a floor of 1,
        # regardless of workforce need.
        plan = settlement_plan(population=0)

        self.assertEqual(plan.milling.recommended_buildings, 1)
        self.assertEqual(plan.baking.recommended_buildings, 1)
        self.assertEqual(plan.recommended_granaries, 1)
        # Farming isn't in the "always" list - no farmland need, no
        # shelter recommended.
        self.assertEqual(plan.farming.recommended_buildings, 0)

    def test_combine_milling_and_baking_at_and_below_threshold(self):
        from economy.constants import SMALL_SETTLEMENT_POPULATION_THRESHOLD

        at_threshold = settlement_plan(population=SMALL_SETTLEMENT_POPULATION_THRESHOLD)
        below_threshold = settlement_plan(
            population=SMALL_SETTLEMENT_POPULATION_THRESHOLD - 1
        )
        above_threshold = settlement_plan(
            population=SMALL_SETTLEMENT_POPULATION_THRESHOLD + 1
        )

        self.assertTrue(at_threshold.combine_milling_and_baking)
        self.assertTrue(below_threshold.combine_milling_and_baking)
        self.assertFalse(above_threshold.combine_milling_and_baking)

    def test_farming_recommended_once_workers_are_needed(self):
        plan = settlement_plan(population=5000)

        self.assertGreater(plan.farming.workers_needed, 0)
        self.assertEqual(plan.farming.recommended_buildings, 1)

    def test_workforce_scales_up_with_population(self):
        # Not a fixed ratio (workers_needed rounds up via math.ceil, so the
        # exact ratio between two sizes is sensitive to rounding noise at
        # small scale) - just confirms the constant-derived formula
        # produces strictly more workers for more residents, whatever the
        # constants are tuned to. Exact per-size values are already pinned
        # down by _assert_plan_matches_population above.
        small = settlement_plan(population=100)
        large = settlement_plan(population=10_000)

        self.assertGreater(large.daily_bread_demand, small.daily_bread_demand)
        self.assertGreater(large.baking.workers_needed, small.baking.workers_needed)
        self.assertGreater(large.milling.workers_needed, small.milling.workers_needed)
        self.assertGreater(large.farming.workers_needed, small.farming.workers_needed)

    def test_requires_exactly_one_argument(self):
        with self.assertRaises(ValueError):
            settlement_plan()

    def test_rejects_both_arguments(self):
        centre = PopulationCentre(name="Both", location=Point(0, 0, srid=3857))
        with self.assertRaises(ValueError):
            settlement_plan(population_centre=centre, population=100)


class SettlementPlanFromPopulationCentreTests(TestCase):
    """
    settlement_plan(population_centre=centre) should agree exactly with
    settlement_plan(population=centre.resident_count) - the two entry
    points are meant to be equivalent, not independently-derived.
    """

    def _make_centre(self, resident_count):
        centre = PopulationCentre.objects.create(
            name="Planningville", location=Point(0, 0, srid=3857)
        )
        patcher = patch.object(
            PopulationCentre,
            "resident_count",
            new_callable=PropertyMock,
            return_value=resident_count,
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        return centre

    def test_matches_equivalent_population_call(self):
        centre = self._make_centre(resident_count=250)

        by_centre = settlement_plan(population_centre=centre)
        by_population = settlement_plan(population=250)

        self.assertEqual(by_centre, by_population)
        self.assertEqual(by_centre.resident_count, 250)
        self.assertEqual(by_centre.daily_bread_demand, by_population.daily_bread_demand)
        self.assertEqual(by_centre.farming, by_population.farming)
        self.assertEqual(by_centre.milling, by_population.milling)
        self.assertEqual(by_centre.baking, by_population.baking)
        self.assertEqual(
            by_centre.recommended_granaries, by_population.recommended_granaries
        )

    def test_zero_resident_centre(self):
        centre = self._make_centre(resident_count=0)

        plan = settlement_plan(population_centre=centre)

        self.assertEqual(plan.daily_bread_demand, 0.0)
        self.assertEqual(plan.farming.workers_needed, 0)
        self.assertEqual(plan.milling.recommended_buildings, 1)
