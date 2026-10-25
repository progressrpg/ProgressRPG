from django.contrib.gis.geos import Point
from django.core.management import call_command
from django.test import TestCase

from character.models import Character
from locations.models import Building, Journey, Node
from locations.constants import PROJECT_SRID


class PlaceCharactersEndsActiveJourneyTests(TestCase):
    """
    place_characters used to write status="cancelled" for a mid-journey
    character being re-placed - a value nothing else in the codebase
    recognises (is_complete only checks "complete", and neither the
    uniq_active_journey_per_character constraint nor any queryset treats it
    as terminal). Regression test for reusing Journey.cancel() instead.
    """

    def setUp(self):
        self.building = Building.objects.create(
            name="Cottage", building_type="residential"
        )
        self.building_node = Node.objects.create(
            name="Cottage entrance",
            location=Point(0, 0, srid=PROJECT_SRID),
            building=self.building,
            kind=Node.Kind.BUILDING,
        )
        self.elsewhere_node = Node.objects.create(
            name="Elsewhere",
            location=Point(100, 100, srid=PROJECT_SRID),
        )
        self.destination_node = Node.objects.create(
            name="Destination",
            location=Point(200, 200, srid=PROJECT_SRID),
        )

        self.character = Character.objects.create(
            given_name="Wanderer",
            location=self.elsewhere_node.location,
            current_node=self.elsewhere_node,
            is_moving=True,
        )
        self.journey = Journey.objects.create(
            character=self.character,
            start_node=self.elsewhere_node,
            destination_node=self.destination_node,
            path_nodes=[self.elsewhere_node.pk, self.destination_node.pk],
            status=Journey.Status.ACTIVE,
        )

    def test_ends_the_journey_as_complete_not_cancelled(self):
        call_command("place_characters")

        self.journey.refresh_from_db()
        self.assertEqual(self.journey.status, Journey.Status.COMPLETE)
        self.assertIsNotNone(self.journey.finished_at)

    def test_clears_is_moving_via_cancel(self):
        call_command("place_characters")

        self.character.refresh_from_db()
        self.assertFalse(self.character.is_moving)
