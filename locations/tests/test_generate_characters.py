"""
Tests for the generate_characters management command - specifically that
generate_for_centre sizes a village's cast from
population_estimation.starting_population (residential capacity), not a
hardcoded per-building ratio.
"""

from django.contrib.gis.geos import Point, Polygon
from django.core.management import call_command
from django.test import TestCase

from character.models import Character, CharacterLocation
from locations.management.commands.generate_characters import Command
from locations.models import Building, PopulationCentre
from locations.services import population_estimation


def _characters_housed_in(building):
    return Character.objects.filter(
        locations__location=building,
        locations__role=CharacterLocation.Role.HOME,
        locations__is_primary=True,
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


class GenerateForCentreTests(TestCase):
    def _make_centre(self, name="Charactertown"):
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

    def test_character_count_matches_starting_population(self):
        centre = self._make_centre()
        for x in range(4):
            self._make_residential_building(centre, size=30, x=x * 40)

        expected = population_estimation.starting_population(centre)
        self.assertGreater(expected, 0)

        call_command("generate_characters", centre=centre.id)

        self.assertEqual(
            Character.objects.filter(population_centre=centre).count(), expected
        )

    def test_zero_capacity_centre_gets_no_characters(self):
        centre = self._make_centre()

        call_command("generate_characters", centre=centre.id)

        self.assertEqual(Character.objects.filter(population_centre=centre).count(), 0)

    def test_generated_characters_are_housed_in_residential_buildings(self):
        centre = self._make_centre()
        building = self._make_residential_building(centre, size=30, x=0)

        call_command("generate_characters", centre=centre.id)

        characters = Character.objects.filter(population_centre=centre)
        self.assertGreater(characters.count(), 0)
        for character in characters:
            self.assertEqual(character.home, building)

    def test_no_building_exceeds_its_own_capacity(self):
        # Regression test: home assignment used to be a uniform
        # random.choice() across all residential buildings, so a small
        # house was just as likely to be picked as a large one and could
        # end up massively overcrowded even though the *centre's* total
        # stayed under its combined capacity. Home slots are now weighted
        # by each building's own residential_capacity.
        centre = self._make_centre()
        small = self._make_residential_building(centre, size=15, x=0)
        large = self._make_residential_building(centre, size=60, x=40)

        call_command("generate_characters", centre=centre.id)

        for building in (small, large):
            count = _characters_housed_in(building).count()
            self.assertLessEqual(
                count, population_estimation.residential_capacity(building)
            )


class AssignHouseholdsToBuildingsTests(TestCase):
    def _make_centre(self, name="Charactertown"):
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

    def test_household_is_kept_together_in_one_building(self):
        centre = self._make_centre()
        building = self._make_residential_building(centre, size=60, x=0)
        household = [Character.objects.create(given_name=f"C{i}") for i in range(3)]

        Command()._assign_households_to_buildings([household], [building])

        for char in household:
            char.refresh_from_db()
            self.assertEqual(char.home, building)

    def test_household_larger_than_any_single_building_spills_across_buildings(self):
        centre = self._make_centre()
        small_a = self._make_residential_building(centre, size=15, x=0)
        small_b = self._make_residential_building(centre, size=15, x=40)
        cap_a = population_estimation.residential_capacity(small_a)
        cap_b = population_estimation.residential_capacity(small_b)
        household = [
            Character.objects.create(given_name=f"C{i}") for i in range(cap_a + cap_b)
        ]

        Command()._assign_households_to_buildings([household], [small_a, small_b])

        for char in household:
            char.refresh_from_db()
        self.assertLessEqual(_characters_housed_in(small_a).count(), cap_a)
        self.assertLessEqual(_characters_housed_in(small_b).count(), cap_b)
        # Combined capacity exactly matches the household, so everyone still
        # ends up housed somewhere - just not all in the same building.
        self.assertTrue(all(char.home is not None for char in household))

    def test_household_exceeding_total_capacity_leaves_remainder_unhoused(self):
        centre = self._make_centre()
        building = self._make_residential_building(centre, size=15, x=0)
        cap = population_estimation.residential_capacity(building)
        household = [
            Character.objects.create(given_name=f"C{i}") for i in range(cap + 2)
        ]

        Command()._assign_households_to_buildings([household], [building])

        for char in household:
            char.refresh_from_db()
        self.assertLessEqual(_characters_housed_in(building).count(), cap)
        self.assertEqual(sum(1 for c in household if c.home is not None), cap)
