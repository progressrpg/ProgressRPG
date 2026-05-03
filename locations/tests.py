from django.contrib.gis.geos import Point
from django.test import TestCase
from unittest.mock import patch

from .models import Node, Path, Building, Journey
from character.models import Character


class LocationsModelsTestCase(TestCase):
    def setUp(self):
        # Create a small linear graph of three nodes
        self.node_a = Node.objects.create(name="A", location=Point(0, 0, srid=3857))
        self.node_b = Node.objects.create(name="B", location=Point(10, 0, srid=3857))
        self.node_c = Node.objects.create(name="C", location=Point(20, 0, srid=3857))

        # Create directed paths A -> B -> C
        self.path_ab = Path.objects.create(from_node=self.node_a, to_node=self.node_b)
        self.path_bc = Path.objects.create(from_node=self.node_b, to_node=self.node_c)

        # Building near node B
        self.building = Building.objects.create(
            name="Test Inn",
            building_type="inn",
            location=Point(10, 0, srid=3857),
        )

        # Link building to node_b for semantic tests
        self.node_b.building = self.building
        self.node_b.save(update_fields=["building"])

    def test_path_length_and_neighbours(self):
        # Path length should be set on save and neighbours() should return expected node
        # Distance between A and B is 10 units
        self.assertIsNotNone(self.path_ab.length)
        self.assertAlmostEqual(
            self.path_ab.length,
            self.node_a.location.distance(self.node_b.location),
            places=6,
        )

        neighbours_of_a = list(self.node_a.neighbours())
        self.assertIn(self.node_b, neighbours_of_a)

    def test_movable_move_to_and_nearby_objects(self):
        # Create a character located at node A
        char = Character.objects.create(
            first_name="Mover",
            location=Point(0, 0, srid=3857),
            current_node=self.node_a,
        )

        # Move instantly to node B
        char.move_to(self.node_b)
        char.refresh_from_db()
        self.assertEqual(char.current_node, self.node_b)
        self.assertEqual(char.location.x, self.node_b.location.x)
        self.assertFalse(char.is_moving)

        # nearby_objects should find the building at node B within a small radius
        nearby = list(char.nearby_objects(Building.objects.all(), radius=1.0))
        # building is exactly at same coordinates as char after move, so should be returned
        self.assertTrue(any(b.pk == self.building.pk for b in nearby))

    def test_set_destination_creates_journey_and_triggers_task(self):
        # Patch out the async task to avoid side effects
        with patch("locations.tasks.move_characters_tick.apply_async") as mocked_task:
            char = Character.objects.create(
                first_name="Walker",
                location=Point(0, 0, srid=3857),
                current_node=self.node_a,
            )

            # Ensure there is no journey initially
            self.assertFalse(hasattr(char, "journey") and char.journey)

            # Set destination to node C - should create a Journey that goes A -> B -> C
            char.set_destination(node=self.node_c)

            char.refresh_from_db()
            # Character should be marked moving and a Journey should exist
            self.assertTrue(char.is_moving)

            # There should be exactly one Journey for this character in DB
            journey = Journey.objects.filter(character=char).first()
            self.assertIsNotNone(journey)

            # The saved path_nodes should include the nodes A, B, C in some order
            self.assertIsInstance(journey.path_nodes, list)
            self.assertGreaterEqual(len(journey.path_nodes), 2)

            # The task should be scheduled because this is the first moving character
            mocked_task.assert_called()

    def test_journey_serialize_and_advance(self):
        # Create a Journey manually spanning A -> B -> C
        journey = Journey.objects.create(
            character=Character.objects.create(
                first_name="J",
                location=Point(0, 0, srid=3857),
                current_node=self.node_a,
            ),
            start_node=self.node_a,
            destination_node=self.node_c,
            path_nodes=[self.node_a.pk, self.node_b.pk, self.node_c.pk],
            current_index=0,
            status="active",
        )

        serialized = journey.serialize_for_client()
        self.assertIn("path", serialized)
        self.assertIn("segment_distances", serialized)
        self.assertEqual(serialized["current_index"], 0)

        # Advance once: should return True and increment index
        progressed = journey.advance_node()
        self.assertTrue(progressed)
        journey.refresh_from_db()
        self.assertEqual(journey.current_index, 1)
        self.assertEqual(journey.current_node(), self.node_b)
        self.assertEqual(journey.next_node(), self.node_c)

        # Advance twice to finish
        progressed = journey.advance_node()
        self.assertTrue(progressed)
        journey.refresh_from_db()
        self.assertEqual(journey.current_index, 2)
        self.assertIsNone(journey.next_node())

        progressed = journey.advance_node()
        self.assertFalse(progressed)
        journey.refresh_from_db()
        self.assertEqual(journey.status, "complete")
        self.assertIsNotNone(journey.finished_at)
