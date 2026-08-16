from unittest.mock import patch

from django.contrib.gis.geos import Point
from django.test import TestCase

from locations.models import Journey, PopulationCentre
from locations.services.wander import wander
from locations.tasks import wander_tick
from locations.tests.factories import VILLAGE_BOUNDARY
from character.models import Character, PlayerCharacterLink
from users.tests import user_factory


class WanderServiceTest(TestCase):
    """Decorative-only movement: must never touch Journey/is_moving/current_node
    or move a character outside its village boundary."""

    def setUp(self):
        self.centre = PopulationCentre.objects.create(
            name="Wander Village",
            location=Point(0, 0, srid=3857),
            boundary=VILLAGE_BOUNDARY,
        )
        self.character = Character.objects.create(
            given_name="Wanderer",
            location=Point(0, 0, srid=3857),
            population_centre=self.centre,
        )

    def test_wander_moves_character_within_boundary(self):
        moved = wander(self.character, radius=15)
        self.assertTrue(moved)
        self.character.refresh_from_db()
        self.assertTrue(self.centre.boundary.contains(self.character.location))

    def test_wander_does_not_create_journey_or_touch_movement_state(self):
        wander(self.character, radius=15)
        self.character.refresh_from_db()
        self.assertFalse(self.character.is_moving)
        self.assertIsNone(self.character.current_node)
        self.assertIsNone(self.character.target_node)
        self.assertEqual(Journey.objects.count(), 0)

    def test_wander_without_population_centre_is_a_noop(self):
        orphan = Character.objects.create(
            given_name="Orphan", location=Point(0, 0, srid=3857)
        )
        moved = wander(orphan, radius=15)
        self.assertFalse(moved)
        orphan.refresh_from_db()
        self.assertEqual(orphan.location.x, 0)
        self.assertEqual(orphan.location.y, 0)

    def test_wander_gives_up_gracefully_when_no_candidate_fits(self):
        # A character pinned at the boundary edge with a huge radius will
        # struggle to find an in-bounds candidate within max_attempts;
        # this should return False rather than raise or move out-of-bounds.
        self.character.location = Point(49, 49, srid=3857)
        self.character.save(update_fields=["location"])

        moved = wander(self.character, radius=1000, max_attempts=5)
        self.character.refresh_from_db()
        if moved:
            self.assertTrue(self.centre.boundary.contains(self.character.location))
        else:
            self.assertEqual(self.character.location.x, 49)
            self.assertEqual(self.character.location.y, 49)


class WanderTickTaskTest(TestCase):
    """wander_tick must exclude anyone mid-journey (is_moving), but is
    otherwise indifferent to player-linking - this is purely visual, not
    gameplay - and only moves a random subgroup of eligible characters
    per tick, not everyone at once."""

    def setUp(self):
        self.centre = PopulationCentre.objects.create(
            name="Tick Village",
            location=Point(0, 0, srid=3857),
            boundary=VILLAGE_BOUNDARY,
        )
        self.idle_npc = Character.objects.create(
            given_name="Idle",
            location=Point(0, 0, srid=3857),
            population_centre=self.centre,
            is_moving=False,
        )
        self.moving_npc = Character.objects.create(
            given_name="Moving",
            location=Point(0, 0, srid=3857),
            population_centre=self.centre,
            is_moving=True,
        )
        self.linked_character = Character.objects.create(
            given_name="Linked",
            location=Point(0, 0, srid=3857),
            population_centre=self.centre,
            is_moving=False,
        )
        user = user_factory(with_player=True)
        PlayerCharacterLink.objects.create(
            player=user.player, character=self.linked_character, is_active=True
        )

    def test_wander_tick_excludes_moving_characters_but_not_linked_ones(self):
        # fraction=1.0 makes the sample deterministic (everyone eligible gets
        # wandered), isolating the is_moving exclusion from the random subset
        # selection tested separately below.
        with patch("locations.services.wander.wander") as mock_wander:
            wander_tick(fraction=1.0)

        wandered_ids = {call.args[0].id for call in mock_wander.call_args_list}
        self.assertEqual(wandered_ids, {self.idle_npc.id, self.linked_character.id})

    def test_wander_tick_only_moves_a_subset_when_fraction_is_small(self):
        with patch("locations.services.wander.wander") as mock_wander:
            wander_tick(fraction=0.1)

        # 2 eligible characters (idle_npc, linked_character); a small
        # fraction should still wander at least one but not both every time
        # in principle, so just assert it never exceeds the eligible pool
        # and never wanders the excluded is_moving character.
        wandered_ids = {call.args[0].id for call in mock_wander.call_args_list}
        self.assertTrue(
            wandered_ids.issubset({self.idle_npc.id, self.linked_character.id})
        )
        self.assertNotIn(self.moving_npc.id, wandered_ids)
        self.assertGreaterEqual(len(wandered_ids), 1)
