from django.contrib.gis.geos import Point
from django.test import TestCase

from locations.models import Building, InteriorSpace, Node, Path, Journey
from locations.serializers import (
    CharacterPointFeatureSerializer,
    JOURNEY_PATH_PREVIEW_LIMIT,
)
from character.models import Character


class CharacterPointFeatureSerializerJourneyTest(TestCase):
    """Path-aware movement interpolation (#615): the map feature for a
    character exposes their remaining journey (capped) and effective speed,
    so the frontend can walk them along the real path instead of tweening
    blindly between two polled points."""

    def setUp(self):
        self.node_a = Node.objects.create(name="A", location=Point(0, 0, srid=3857))
        self.node_b = Node.objects.create(name="B", location=Point(10, 0, srid=3857))
        self.node_c = Node.objects.create(name="C", location=Point(20, 0, srid=3857))
        Path.objects.create(from_node=self.node_a, to_node=self.node_b)
        Path.objects.create(from_node=self.node_b, to_node=self.node_c)

    def test_idle_character_has_no_path(self):
        character = Character.objects.create(
            given_name="Idle",
            location=Point(0, 0, srid=3857),
            current_node=self.node_a,
            movement_speed=2.5,
        )

        props = CharacterPointFeatureSerializer(character).data["properties"]

        self.assertIsNone(props["path"])
        self.assertEqual(props["effective_speed"], 2.5)

    def test_moving_character_exposes_remaining_path_and_speed(self):
        character = Character.objects.create(
            given_name="Walker",
            location=Point(0, 0, srid=3857),
            current_node=self.node_a,
            is_moving=True,
            movement_speed=3.0,
        )
        Journey.objects.create(
            character=character,
            start_node=self.node_a,
            destination_node=self.node_c,
            path_nodes=[self.node_a.pk, self.node_b.pk, self.node_c.pk],
            current_index=0,
            status="active",
        )

        props = CharacterPointFeatureSerializer(character).data["properties"]

        self.assertEqual(props["path"], [[10.0, 0.0], [20.0, 0.0]])
        self.assertEqual(props["effective_speed"], 3.0)

    def test_path_is_capped_to_preview_limit(self):
        nodes = [self.node_a, self.node_b, self.node_c]
        for i in range(JOURNEY_PATH_PREVIEW_LIMIT + 5):
            nodes.append(
                Node.objects.create(
                    name=f"Extra{i}", location=Point(30 + i * 10, 0, srid=3857)
                )
            )
            Path.objects.create(from_node=nodes[-2], to_node=nodes[-1])

        character = Character.objects.create(
            given_name="LongHauler",
            location=Point(0, 0, srid=3857),
            current_node=self.node_a,
            is_moving=True,
        )
        Journey.objects.create(
            character=character,
            start_node=self.node_a,
            destination_node=nodes[-1],
            path_nodes=[n.pk for n in nodes],
            current_index=0,
            status="active",
        )

        props = CharacterPointFeatureSerializer(character).data["properties"]

        self.assertEqual(len(props["path"]), JOURNEY_PATH_PREVIEW_LIMIT)


class CharacterPointFeatureSerializerLocationTypeTest(TestCase):
    """current_location_type/destination_location_type feed the map
    tooltip's "[Activity] at [building]" / "Walking to [building]" copy
    (issue: concise contextual character tooltip) - None means the node
    isn't inside a building at all, so the tooltip reads "outside"."""

    def setUp(self):
        self.bakery = Building.objects.create(
            name="Bakery 1", building_type="bakery", location=Point(0, 0, srid=3857)
        )
        self.building_node = Node.objects.create(
            name="Bakery entrance",
            location=Point(0, 0, srid=3857),
            building=self.bakery,
        )
        self.outside_node = Node.objects.create(
            name="Field", location=Point(50, 50, srid=3857)
        )

    def test_current_location_type_reflects_the_building_the_character_is_in(self):
        character = Character.objects.create(
            given_name="Baker",
            location=Point(0, 0, srid=3857),
            current_node=self.building_node,
        )

        props = CharacterPointFeatureSerializer(character).data["properties"]

        self.assertEqual(props["current_location_type"], "bakery")

    def test_current_location_type_reflects_the_building_of_an_interior_node(self):
        # Interior nodes (kind=INTERIOR) only set interior_space, not
        # building directly (Node.building/interior_space are mutually
        # exclusive - see the node_building_or_interior constraint), so a
        # character in a room deep inside the bakery still needs to resolve
        # back to that building rather than reading as "outside".
        kitchen = InteriorSpace.objects.create(
            name="Kitchen", building=self.bakery, area=20, usage="kitchen"
        )
        interior_node = Node.objects.create(
            name="Kitchen floor",
            location=Point(0, 0, srid=3857),
            interior_space=kitchen,
        )
        character = Character.objects.create(
            given_name="Kneader",
            location=Point(0, 0, srid=3857),
            current_node=interior_node,
        )

        props = CharacterPointFeatureSerializer(character).data["properties"]

        self.assertEqual(props["current_location_type"], "bakery")

    def test_current_location_type_is_none_when_the_character_is_outside(self):
        character = Character.objects.create(
            given_name="Forager",
            location=Point(50, 50, srid=3857),
            current_node=self.outside_node,
        )

        props = CharacterPointFeatureSerializer(character).data["properties"]

        self.assertIsNone(props["current_location_type"])

    def test_destination_location_type_reflects_the_journeys_destination_building(
        self,
    ):
        character = Character.objects.create(
            given_name="Walker",
            location=Point(50, 50, srid=3857),
            current_node=self.outside_node,
            is_moving=True,
        )
        Journey.objects.create(
            character=character,
            start_node=self.outside_node,
            destination_node=self.building_node,
            path_nodes=[self.outside_node.pk, self.building_node.pk],
            current_index=0,
            status="active",
        )

        props = CharacterPointFeatureSerializer(character).data["properties"]

        self.assertEqual(props["destination_location_type"], "bakery")

    def test_destination_location_type_is_none_when_walking_to_a_spot_with_no_building(
        self,
    ):
        character = Character.objects.create(
            given_name="Wanderer",
            location=Point(0, 0, srid=3857),
            current_node=self.building_node,
            is_moving=True,
        )
        Journey.objects.create(
            character=character,
            start_node=self.building_node,
            destination_node=self.outside_node,
            path_nodes=[self.building_node.pk, self.outside_node.pk],
            current_index=0,
            status="active",
        )

        props = CharacterPointFeatureSerializer(character).data["properties"]

        self.assertIsNone(props["destination_location_type"])
