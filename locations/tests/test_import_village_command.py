from django.contrib.gis.geos import Point
from django.core.management.base import CommandError
from django.test import TestCase

from locations.management.commands.import_village import Command
from locations.models import PopulationCentre
from locations.village_layout import VILLAGE_LAYOUT


class ResolveOriginTest(TestCase):
    def setUp(self):
        self.command = Command()

    def test_both_x_and_y_given_uses_them_directly(self):
        origin = self.command._resolve_origin(123, 456)
        self.assertEqual(origin, Point(123, 456, srid=3857))

    def test_only_x_given_raises(self):
        with self.assertRaises(CommandError):
            self.command._resolve_origin(123, None)

    def test_only_y_given_raises(self):
        with self.assertRaises(CommandError):
            self.command._resolve_origin(None, 456)

    def test_neither_given_auto_picks_a_slot(self):
        origin = self.command._resolve_origin(None, None)
        x, y = VILLAGE_LAYOUT[0]
        self.assertEqual(origin, Point(x, y, srid=3857))


class PickUnusedLayoutSlotTest(TestCase):
    def setUp(self):
        self.command = Command()

    def test_picks_first_slot_when_none_occupied(self):
        origin = self.command._pick_unused_layout_slot()
        x, y = VILLAGE_LAYOUT[0]
        self.assertEqual(origin, Point(x, y, srid=3857))

    def test_skips_occupied_slots(self):
        first_x, first_y = VILLAGE_LAYOUT[0]
        second_x, second_y = VILLAGE_LAYOUT[1]
        PopulationCentre.objects.create(
            name="Occupied village",
            location=Point(first_x, first_y, srid=3857),
        )

        origin = self.command._pick_unused_layout_slot()

        self.assertEqual(origin, Point(second_x, second_y, srid=3857))

    def test_raises_when_every_slot_is_occupied(self):
        for i, (x, y) in enumerate(VILLAGE_LAYOUT):
            PopulationCentre.objects.create(
                name=f"Village {i}",
                location=Point(x, y, srid=3857),
            )

        with self.assertRaises(CommandError):
            self.command._pick_unused_layout_slot()

    def test_ignores_centres_not_on_a_layout_slot(self):
        # A centre placed off-grid (e.g. hand-picked --x/--y) shouldn't
        # affect which layout slots count as unoccupied.
        PopulationCentre.objects.create(
            name="Off-grid village",
            location=Point(999_999, 999_999, srid=3857),
        )

        origin = self.command._pick_unused_layout_slot()
        x, y = VILLAGE_LAYOUT[0]
        self.assertEqual(origin, Point(x, y, srid=3857))
