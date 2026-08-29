"""
Tests for locations.services.movement.step_toward - the per-tick distance
budget that drives character movement.

This is the logic the frontend walker animation has to agree with: the client
interpolates between polls from a checkpoint plus elapsed time (see
Map.tsx's walkersRef), so if the server spends a tick's budget differently
the two visibly diverge. test_models.py covers Journey bookkeeping and
asserts a full tick "does not raise"; this covers how far a character
actually gets.

step_toward mutates the movable in memory and leaves saving to its caller
(move_characters_tick's bulk_update), so these assertions read the in-memory
object. Journey rows are saved by advance_node()/arrive() and are re-read
from the DB.
"""

from django.contrib.gis.geos import Point
from django.test import TestCase

from character.models import Character, CharacterLocation
from locations.models import Building, Journey, Node, Path
from locations.services.movement import find_path, go_home, go_outside, step_toward
from locations.constants import PROJECT_SRID


class StepTowardTests(TestCase):
    def setUp(self):
        # Linear graph: A(0,0) -> B(10,0) -> C(20,0). Ten units per segment,
        # and movement_speed defaults to 1.0, so a time_delta of N gives a
        # budget of exactly N units.
        self.node_a = Node.objects.create(
            name="A", location=Point(0, 0, srid=PROJECT_SRID)
        )
        self.node_b = Node.objects.create(
            name="B", location=Point(10, 0, srid=PROJECT_SRID)
        )
        self.node_c = Node.objects.create(
            name="C", location=Point(20, 0, srid=PROJECT_SRID)
        )
        Path.objects.create(from_node=self.node_a, to_node=self.node_b)
        Path.objects.create(from_node=self.node_b, to_node=self.node_c)

        self.character = Character.objects.create(
            given_name="Walker",
            location=Point(0, 0, srid=PROJECT_SRID),
            current_node=self.node_a,
            is_moving=True,
        )
        self.journey = Journey.objects.create(
            character=self.character,
            start_node=self.node_a,
            destination_node=self.node_c,
            path_nodes=[self.node_a.pk, self.node_b.pk, self.node_c.pk],
            current_index=0,
        )

    def test_stops_partway_along_a_segment(self):
        still_moving = step_toward(self.character, time_delta=4.0)

        self.assertTrue(still_moving)
        self.assertAlmostEqual(self.character.location.x, 4.0)
        self.assertAlmostEqual(self.character.location.y, 0.0)
        # Not yet reached B, so the current node is unchanged.
        self.assertEqual(self.character.current_node, self.node_a)
        self.assertTrue(self.character.is_moving)

    def test_spends_one_budget_across_several_segments(self):
        """
        The behaviour the budget loop exists for: a 15-unit budget crosses
        the whole 10-unit A->B segment and continues 5 units into B->C,
        rather than being dropped at B and resuming next tick - which would
        make a character visibly stall at every node.
        """
        still_moving = step_toward(self.character, time_delta=15.0)

        self.assertTrue(still_moving)
        self.assertAlmostEqual(self.character.location.x, 15.0)
        self.assertAlmostEqual(self.character.location.y, 0.0)
        # Passed through B, so that is now the node behind them.
        self.assertEqual(self.character.current_node, self.node_b)

        self.journey.refresh_from_db()
        self.assertEqual(self.journey.current_index, 1)
        self.assertFalse(self.journey.is_complete)

    def test_speed_modifier_scales_the_budget(self):
        step_toward(self.character, time_delta=4.0, speed_modifier=2.0)

        self.assertAlmostEqual(self.character.location.x, 8.0)

    def test_movement_speed_scales_the_budget(self):
        self.character.movement_speed = 3.0

        step_toward(self.character, time_delta=2.0)

        self.assertAlmostEqual(self.character.location.x, 6.0)

    def test_arrives_when_the_budget_covers_the_whole_path(self):
        still_moving = step_toward(self.character, time_delta=100.0)

        self.assertFalse(still_moving)
        self.assertEqual(self.character.current_node, self.node_c)
        self.assertAlmostEqual(self.character.location.x, 20.0)
        self.assertFalse(self.character.is_moving)
        self.assertIsNone(self.character.target_node)

        self.journey.refresh_from_db()
        self.assertTrue(self.journey.is_complete)
        self.assertIsNotNone(self.journey.finished_at)

    def test_arrival_is_exact_rather_than_wherever_the_budget_ran_out(self):
        """A budget overshooting the destination still lands on the node."""
        step_toward(self.character, time_delta=23.0)

        self.assertEqual(self.character.location.x, self.node_c.location.x)
        self.assertEqual(self.character.location.y, self.node_c.location.y)

    def test_two_ticks_reach_the_same_place_as_one_of_equal_total_budget(self):
        """
        Movement is a function of elapsed time, not of how many ticks that
        time is split across - what lets move_characters_tick measure its own
        real gap rather than assuming a fixed cadence.
        """
        step_toward(self.character, time_delta=7.0)
        step_toward(self.character, time_delta=8.0)

        self.assertAlmostEqual(self.character.location.x, 15.0)
        self.assertEqual(self.character.current_node, self.node_b)

    def test_no_active_journey_clears_the_moving_flag(self):
        self.journey.delete()
        # _journey is the transient cache movement services set; without it
        # step_toward falls back to querying, and finds nothing.
        self.character._journey = None

        still_moving = step_toward(self.character, time_delta=5.0)

        self.assertFalse(still_moving)
        self.assertFalse(self.character.is_moving)
        # Position untouched: there was nowhere to go.
        self.assertAlmostEqual(self.character.location.x, 0.0)

    def test_completed_journey_clears_the_moving_flag(self):
        self.journey.status = "complete"
        self.journey.save(update_fields=["status"])
        self.character._journey = None

        still_moving = step_toward(self.character, time_delta=5.0)

        self.assertFalse(still_moving)
        self.assertFalse(self.character.is_moving)


class FindPathTests(TestCase):
    """
    find_path is self-described in its own comment as "very dumb: pick
    first outgoing path until we reach the end" - these pin what it
    actually does (BFS via Node.neighbours(), stopping at the first route
    found) rather than asserting an idealized shortest-path guarantee it
    doesn't provide.
    """

    def setUp(self):
        # Linear graph A-B-C, plus an unconnected D.
        self.node_a = Node.objects.create(
            name="A", location=Point(0, 0, srid=PROJECT_SRID)
        )
        self.node_b = Node.objects.create(
            name="B", location=Point(10, 0, srid=PROJECT_SRID)
        )
        self.node_c = Node.objects.create(
            name="C", location=Point(20, 0, srid=PROJECT_SRID)
        )
        self.node_d = Node.objects.create(
            name="D", location=Point(100, 100, srid=PROJECT_SRID)
        )
        Path.objects.create(from_node=self.node_a, to_node=self.node_b)
        Path.objects.create(from_node=self.node_b, to_node=self.node_c)

    def test_direct_single_hop_connection(self):
        self.assertEqual(
            find_path(self.node_a, self.node_b), [self.node_a, self.node_b]
        )

    def test_walks_through_an_intermediate_node(self):
        self.assertEqual(
            find_path(self.node_a, self.node_c),
            [self.node_a, self.node_b, self.node_c],
        )

    def test_returns_none_when_no_path_exists(self):
        self.assertIsNone(find_path(self.node_a, self.node_d))

    def test_start_equals_end_returns_a_single_node_path(self):
        self.assertEqual(find_path(self.node_a, self.node_a), [self.node_a])


class GoHomeTests(TestCase):
    def setUp(self):
        self.start_node = Node.objects.create(
            name="Start", location=Point(0, 0, srid=PROJECT_SRID)
        )
        self.building = Building.objects.create(
            name="Cottage",
            building_type="residential",
            location=Point(10, 0, srid=PROJECT_SRID),
        )
        # BUILDING_ENTRANCE, not BUILDING - go_home looks up the entrance
        # node first, falling back to an interior room's node only if the
        # building has one; no InteriorSpace here keeps this deterministic.
        self.entrance_node = Node.objects.create(
            name="Cottage entrance",
            location=Point(10, 0, srid=PROJECT_SRID),
            building=self.building,
            kind=Node.Kind.BUILDING_ENTRANCE,
        )
        Path.objects.create(from_node=self.start_node, to_node=self.entrance_node)

        self.character = Character.objects.create(
            given_name="Homer",
            location=self.start_node.location,
            current_node=self.start_node,
        )

    def _give_home(self):
        CharacterLocation.objects.create(
            character=self.character,
            location=self.building,
            role=CharacterLocation.Role.HOME,
            is_primary=True,
        )

    def test_character_with_a_home_is_sent_there(self):
        self._give_home()

        result = go_home(self.character)

        self.assertTrue(result)
        self.assertTrue(self.character.is_moving)
        self.assertEqual(self.character.target_node, self.entrance_node)
        self.assertTrue(
            Journey.objects.filter(
                character=self.character, destination_node=self.entrance_node
            ).exists()
        )

    def test_character_with_no_home_is_a_no_op(self):
        result = go_home(self.character)

        self.assertFalse(result)
        self.assertFalse(self.character.is_moving)
        self.assertFalse(Journey.objects.filter(character=self.character).exists())

    def test_character_already_home_is_a_no_op(self):
        self._give_home()
        self.character.current_node = self.entrance_node
        self.character.save(update_fields=["current_node"])

        result = go_home(self.character)

        self.assertFalse(result)
        self.assertFalse(Journey.objects.filter(character=self.character).exists())


class GoOutsideTests(TestCase):
    def setUp(self):
        self.start_node = Node.objects.create(
            name="Start", location=Point(0, 0, srid=PROJECT_SRID)
        )
        self.outside_node = Node.objects.create(
            name="Square",
            location=Point(5, 0, srid=PROJECT_SRID),
            kind=Node.Kind.OUTSIDE,
        )
        Path.objects.create(from_node=self.start_node, to_node=self.outside_node)

        self.character = Character.objects.create(
            given_name="Wanderer",
            location=self.start_node.location,
            current_node=self.start_node,
        )

    def test_destination_lands_within_radius_of_a_nearby_outside_node(self):
        result = go_outside(self.character, radius=100)

        self.assertTrue(result)
        self.assertTrue(self.character.is_moving)
        self.assertEqual(self.character.target_node, self.outside_node)

    def test_no_nearby_outside_node_is_a_no_op(self):
        # outside_node is 5 units away - a radius of 1 excludes it.
        result = go_outside(self.character, radius=1)

        self.assertFalse(result)
        self.assertFalse(self.character.is_moving)
        self.assertFalse(Journey.objects.filter(character=self.character).exists())
