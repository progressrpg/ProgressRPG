from django.test import TestCase

from .models import Position, Movable, Location

from character.models import Character


class PositionModelTests(TestCase):
    def test_calculate_distance(self):
        pos1 = Position.objects.create(x=0, y=0)
        pos2 = Position.objects.create(x=3, y=4)
        distance = pos1.calculate_distance(pos2)
        self.assertEqual(distance, 5.0)  # 3-4-5 triangle

    def test_is_near_true(self):
        pos1 = Position.objects.create(x=0, y=0)
        pos2 = Position.objects.create(x=1, y=1)
        self.assertTrue(pos1.is_near(pos2, threshold=2.0))

    def test_is_near_false(self):
        pos1 = Position.objects.create(x=0, y=0)
        pos2 = Position.objects.create(x=5, y=5)
        self.assertFalse(pos1.is_near(pos2, threshold=2.0))


class LocationModelTests(TestCase):
    def test_create_location(self):
        pos = Position.objects.create(x=10, y=20)
        loc = Location.objects.create(
            name="Test Location", position=pos, description="A test place"
        )
        self.assertEqual(loc.name, "Test Location")
        self.assertEqual(loc.position.x, 10)
        self.assertEqual(loc.position.y, 20)
        self.assertEqual(loc.description, "A test place")

    def test_distance_between_locations(self):
        pos1 = Position.objects.create(x=0, y=0)
        pos2 = Position.objects.create(x=6, y=8)
        loc1 = Location.objects.create(name="Loc1", position=pos1)
        loc2 = Location.objects.create(name="Loc2", position=pos2)
        distance = loc1.position.calculate_distance(loc2.position)
        self.assertEqual(distance, 10.0)  # 6-8-10 triangle


class MovableModelTests(TestCase):
    def setUp(self):
        # Create positions for testing
        self.start_pos = Position.objects.create(x=0, y=0)
        self.end_pos = Position.objects.create(x=3, y=4)  # distance = 5
        # Create a movable object
        self.char = Character.objects.create(name="bob", position=self.start_pos)
        # self.char.position = self.start_pos

    def test_move_to_updates_position(self):
        travel_time = self.char.move_to(self.end_pos)
        self.char.refresh_from_db()
        self.assertEqual(self.char.position, self.end_pos)
        self.assertFalse(self.char.is_moving)
        self.assertEqual(travel_time, 5.0)  # distance / speed

    def test_move_to_with_speed_modifier(self):
        travel_time = self.char.move_to(self.end_pos, speed_modifier=2.0)
        # 5 / (1*2) = 2.5
        self.assertEqual(travel_time, 2.5)
