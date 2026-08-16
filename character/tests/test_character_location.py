from django.contrib.gis.geos import Point
from django.db import IntegrityError, transaction
from django.test import TestCase

from character.models import Character, CharacterLocation
from locations.models import Building


class CharacterLocationModelTests(TestCase):
    def setUp(self):
        self.character = Character.objects.create(
            given_name="Homer", location=Point(0, 0, srid=3857)
        )
        self.home = Building.objects.create(
            name="Homer's House",
            building_type="residential",
            location=Point(0, 0, srid=3857),
        )
        self.work = Building.objects.create(
            name="Power Plant",
            building_type="communal",
            location=Point(10, 10, srid=3857),
        )

    def test_create_home_and_work_locations(self):
        home = CharacterLocation.objects.create(
            character=self.character,
            location=self.home,
            role=CharacterLocation.Role.HOME,
        )
        work = CharacterLocation.objects.create(
            character=self.character,
            location=self.work,
            role=CharacterLocation.Role.WORK,
        )
        self.assertEqual(home.role, "home")
        self.assertEqual(work.role, "work")
        self.assertTrue(home.is_primary)

    def test_second_primary_home_raises_integrity_error(self):
        CharacterLocation.objects.create(
            character=self.character,
            location=self.home,
            role=CharacterLocation.Role.HOME,
        )
        other_home = Building.objects.create(
            name="Second House",
            building_type="residential",
            location=Point(1, 1, srid=3857),
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CharacterLocation.objects.create(
                    character=self.character,
                    location=other_home,
                    role=CharacterLocation.Role.HOME,
                )

    def test_non_primary_duplicate_role_is_allowed(self):
        CharacterLocation.objects.create(
            character=self.character,
            location=self.home,
            role=CharacterLocation.Role.HOME,
        )
        other_home = Building.objects.create(
            name="Second House",
            building_type="residential",
            location=Point(1, 1, srid=3857),
        )
        # Not primary, so it doesn't collide with the constraint.
        secondary = CharacterLocation.objects.create(
            character=self.character,
            location=other_home,
            role=CharacterLocation.Role.HOME,
            is_primary=False,
        )
        self.assertFalse(secondary.is_primary)
