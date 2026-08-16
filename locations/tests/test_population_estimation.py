"""
Tests for locations.services.population_estimation - specifically that
resident-capacity figures are always *derived* from
SLEEPING_AREA_PER_RESIDENT_SQM and populate_interiors'
BUILDING_INTERIORS_PROPORTIONS sleeping-space split, not a hardcoded
number, so retuning either automatically flows through - same rationale as
economy/tests/test_capacity_services.py and test_planning_services.py.
"""

import math

from django.contrib.gis.geos import Point, Polygon
from django.test import SimpleTestCase, TestCase

from locations.management.commands.populate_interiors import (
    BUILDING_INTERIORS_PROPORTIONS,
)
from locations.models import Building, PopulationCentre
from locations.services.population_estimation import (
    RESIDENTIAL_OCCUPANCY_FACTOR,
    SLEEPING_AREA_PER_RESIDENT_SQM,
    STARTING_POPULATION_FRACTION_RANGE,
    estimate_population_from_footprint_areas,
    population_capacity,
    residential_capacity,
    starting_population,
)

SLEEPING_FRACTION = BUILDING_INTERIORS_PROPORTIONS["residential"]["sleeping"]


def _expected_capacity(area):
    return math.floor(
        area
        * SLEEPING_FRACTION
        / SLEEPING_AREA_PER_RESIDENT_SQM
        * RESIDENTIAL_OCCUPANCY_FACTOR
    )


def _square_footprint(size, x=0, y=0):
    return Polygon(
        (
            (x, y),
            (x + size, y),
            (x + size, y + size),
            (x, y + size),
            (x, y),
        ),
        srid=3857,
    )


class EstimatePopulationFromFootprintAreasTests(SimpleTestCase):
    """
    estimate_population_from_footprint_areas needs no database - it's pure
    arithmetic over raw areas, for watabou_import's pre-Building-row path.
    """

    def test_zero_area_has_zero_capacity(self):
        self.assertEqual(estimate_population_from_footprint_areas([0.0]), 0)

    def test_single_area_matches_expected_capacity(self):
        area = 200.0
        self.assertEqual(
            estimate_population_from_footprint_areas([area]),
            _expected_capacity(area),
        )

    def test_capacity_scales_with_area(self):
        # Not a fixed ratio (floor() rounds down, so exact proportionality
        # only holds up to rounding noise) - just confirms bigger footprints
        # sleep at least as many residents, however the constants are tuned.
        small = estimate_population_from_footprint_areas([50.0])
        large = estimate_population_from_footprint_areas([5000.0])

        self.assertGreater(large, small)

    def test_multiple_areas_sum(self):
        areas = [100.0, 250.0, 40.0]
        expected = sum(_expected_capacity(area) for area in areas)

        self.assertEqual(estimate_population_from_footprint_areas(areas), expected)

    def test_empty_list_has_zero_capacity(self):
        self.assertEqual(estimate_population_from_footprint_areas([]), 0)


class ResidentialCapacityTests(TestCase):
    """
    residential_capacity/population_capacity need real Building/
    PopulationCentre rows - the "buildings already exist" path.
    """

    def _make_centre(self, name="Estimateville"):
        return PopulationCentre.objects.create(
            name=name, location=Point(0, 0, srid=3857)
        )

    def _make_building(self, centre, building_type, footprint, x=0):
        return Building.objects.create(
            name=f"{building_type} at {x}",
            building_type=building_type,
            location=Point(x, 0, srid=3857),
            footprint=footprint,
            population_centre=centre,
        )

    def test_residential_building_has_nonzero_capacity(self):
        centre = self._make_centre()
        building = self._make_building(
            centre, "residential", _square_footprint(20, x=0)
        )

        expected = _expected_capacity(building.footprint.area)
        self.assertGreater(expected, 0)
        self.assertEqual(residential_capacity(building), expected)

    def test_non_residential_building_is_always_zero(self):
        centre = self._make_centre()
        # A large footprint - if this returned nonzero, it'd mean building
        # type wasn't actually gating the calc.
        building = self._make_building(centre, "granary", _square_footprint(50, x=0))

        self.assertEqual(residential_capacity(building), 0)

    def test_missing_footprint_is_zero(self):
        centre = self._make_centre()
        building = self._make_building(centre, "residential", footprint=None, x=0)

        self.assertEqual(residential_capacity(building), 0)

    def test_population_capacity_sums_residential_and_ignores_others(self):
        centre = self._make_centre()
        house_one = self._make_building(
            centre, "residential", _square_footprint(20, x=0)
        )
        house_two = self._make_building(
            centre, "residential", _square_footprint(15, x=30)
        )
        self._make_building(centre, "granary", _square_footprint(50, x=60))

        expected = _expected_capacity(house_one.footprint.area) + _expected_capacity(
            house_two.footprint.area
        )
        self.assertEqual(population_capacity(centre), expected)

    def test_population_capacity_is_zero_for_centre_with_no_buildings(self):
        centre = self._make_centre()

        self.assertEqual(population_capacity(centre), 0)

    def test_matches_equivalent_footprint_area_call(self):
        # The two entry points must agree - real Building rows vs. the raw
        # areas watabou_import has before any row exists.
        centre = self._make_centre()
        houses = [
            self._make_building(centre, "residential", _square_footprint(20, x=0)),
            self._make_building(centre, "residential", _square_footprint(35, x=40)),
            self._make_building(centre, "residential", _square_footprint(12, x=90)),
        ]
        self._make_building(centre, "mill", _square_footprint(25, x=140))

        areas = [house.footprint.area for house in houses]

        self.assertEqual(
            population_capacity(centre),
            estimate_population_from_footprint_areas(areas),
        )


class StartingPopulationTests(TestCase):
    """
    starting_population should always be a fraction of population_capacity
    (never the full figure, never negative/crashing at zero capacity), and
    deterministic for a given capacity - see the module docstring for why
    it's seeded on capacity rather than population_centre.id/.name.
    """

    def _make_centre(self, name="Startingville"):
        return PopulationCentre.objects.create(
            name=name, location=Point(0, 0, srid=3857)
        )

    def _make_residential_building(self, centre, size, x=0):
        return Building.objects.create(
            name=f"house at {x}",
            building_type="residential",
            location=Point(x, 0, srid=3857),
            footprint=_square_footprint(size, x=x),
            population_centre=centre,
        )

    def test_zero_capacity_has_zero_starting_population(self):
        centre = self._make_centre()

        self.assertEqual(population_capacity(centre), 0)
        self.assertEqual(starting_population(centre), 0)

    def test_starting_population_is_below_capacity(self):
        centre = self._make_centre()
        for x in range(5):
            self._make_residential_building(centre, size=30, x=x * 40)

        capacity = population_capacity(centre)
        self.assertGreater(capacity, 0)
        self.assertLess(starting_population(centre), capacity)

    def test_starting_population_is_at_least_one_when_capacity_exists(self):
        centre = self._make_centre()
        self._make_residential_building(centre, size=20, x=0)

        capacity = population_capacity(centre)
        self.assertGreater(capacity, 0)
        self.assertGreaterEqual(starting_population(centre), 1)

    def test_starting_population_is_deterministic_for_same_centre(self):
        centre = self._make_centre()
        for x in range(4):
            self._make_residential_building(centre, size=25, x=x * 40)

        self.assertEqual(starting_population(centre), starting_population(centre))

    def test_starting_population_matches_for_equal_capacity(self):
        # Known limitation, not a bug: two different settlements that land
        # on the same capacity get the same starting population, since the
        # seed is derived from capacity alone.
        centre_one = self._make_centre(name="Startingville One")
        self._make_residential_building(centre_one, size=25, x=0)

        centre_two = self._make_centre(name="Startingville Two")
        self._make_residential_building(centre_two, size=25, x=100)

        self.assertEqual(
            population_capacity(centre_one), population_capacity(centre_two)
        )
        self.assertEqual(
            starting_population(centre_one), starting_population(centre_two)
        )

    def test_fraction_range_is_below_one(self):
        # Sanity check on the tunable constant itself - starting population
        # must never reach full capacity, or "room to grow" stops being true.
        low, high = STARTING_POPULATION_FRACTION_RANGE
        self.assertGreater(low, 0)
        self.assertLess(high, 1)
