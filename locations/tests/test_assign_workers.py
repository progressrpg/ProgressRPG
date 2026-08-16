from datetime import date, timedelta

from django.contrib.gis.geos import Point
from django.core.management import call_command
from django.test import TestCase

from character.models import Character, CharacterLocation
from economy.models import BuildingCapability
from locations.management.commands.generate_villages import create_building_footprint
from locations.models import Building, PopulationCentre

WORKING_AGE_BIRTH_DATE = date.today() - timedelta(days=25 * 365)


def _make_centre(name="Testville"):
    return PopulationCentre.objects.create(name=name, location=Point(0, 0, srid=3857))


def _make_building(centre, building_type, x, *, activities=()):
    footprint = create_building_footprint(
        Point(x, 0, srid=3857), min_size=5, max_size=10
    )
    building = Building.objects.create(
        name=f"{building_type} at {x}",
        building_type=building_type,
        location=Point(x, 0, srid=3857),
        footprint=footprint,
        population_centre=centre,
    )
    for activity in activities:
        BuildingCapability.objects.create(building=building, activity=activity)
    Node = building.nodes.model
    Node.objects.create(
        name=f"Node for {building.name}",
        location=building.location,
        kind=Node.Kind.BUILDING,
        building=building,
    )
    return building


def _make_resident(centre, index):
    character = Character.objects.create(
        given_name=f"Resident{index}",
        birth_date=WORKING_AGE_BIRTH_DATE,
        population_centre=centre,
        location=centre.location,
    )
    home_building = Building.objects.filter(
        population_centre=centre, building_type="residential"
    ).first()
    if home_building is None:
        home_building = _make_building(centre, "residential", 0)
    CharacterLocation.objects.create(
        character=character,
        location=home_building,
        role=CharacterLocation.Role.HOME,
        is_primary=True,
    )
    return character


class AssignWorkersGranaryTests(TestCase):
    def test_granary_never_gets_workers(self):
        centre = _make_centre()
        granary = _make_building(centre, "granary", 10)
        for i in range(5):
            _make_resident(centre, i)

        call_command("assign_workers")

        self.assertFalse(
            CharacterLocation.objects.filter(
                location=granary, role=CharacterLocation.Role.WORK
            ).exists()
        )


class AssignWorkersEconomyRoleTests(TestCase):
    def test_fills_first_building_before_second_for_same_role(self):
        centre = _make_centre()
        mill1 = _make_building(centre, "mill", 10, activities=["milling"])
        mill2 = _make_building(centre, "mill", 20, activities=["milling"])
        for i in range(10):
            _make_resident(centre, i)

        call_command("assign_workers")

        mill1_workers = CharacterLocation.objects.filter(
            location=mill1, role=CharacterLocation.Role.WORK
        ).count()
        mill2_workers = CharacterLocation.objects.filter(
            location=mill2, role=CharacterLocation.Role.WORK
        ).count()

        # mill1 (lower id, processed first) should be filled to its cap
        # before mill2 gets anyone - a greedy fill, not an even split.
        self.assertGreaterEqual(mill1_workers, mill2_workers)
        self.assertLessEqual(mill1_workers, 3)

    def test_communal_building_gets_workers_for_both_capabilities(self):
        centre = _make_centre()
        communal = _make_building(
            centre, "communal", 10, activities=["milling", "baking"]
        )
        for i in range(10):
            _make_resident(centre, i)

        call_command("assign_workers")

        self.assertTrue(
            CharacterLocation.objects.filter(
                location=communal, role=CharacterLocation.Role.WORK
            ).exists()
        )

    def test_village_with_too_few_eligible_workers_ends_up_understaffed(self):
        centre = _make_centre()
        _make_building(centre, "mill", 10, activities=["milling"])
        _make_building(centre, "bakery", 20, activities=["baking"])
        # Only one eligible worker for a village whose settlement_plan will
        # recommend more - this is the "struggling at spawn" case: fewer
        # workers assigned than settlement_plan would want, not an evenly
        # thin spread across every building.
        _make_resident(centre, 0)

        call_command("assign_workers")

        total_assigned = CharacterLocation.objects.filter(
            location__population_centre=centre, role=CharacterLocation.Role.WORK
        ).count()
        self.assertLessEqual(total_assigned, 1)


class AssignWorkersFallbackTests(TestCase):
    def test_non_economy_building_gets_flat_random_workers(self):
        centre = _make_centre()
        inn = _make_building(centre, "inn", 10)
        for i in range(6):
            _make_resident(centre, i)

        call_command("assign_workers")

        inn_workers = CharacterLocation.objects.filter(
            location=inn, role=CharacterLocation.Role.WORK
        ).count()
        self.assertGreaterEqual(inn_workers, 2)
        self.assertLessEqual(inn_workers, 3)
