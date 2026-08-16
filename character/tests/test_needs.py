from django.test import TestCase

from economy.constants import HUNGER_MAX

from character.models import Character


class HungerLabelTest(TestCase):
    def setUp(self):
        self.character = Character.objects.create(given_name="Alice")

    def test_below_midpoint_is_well_fed(self):
        self.character.needs.hunger = (HUNGER_MAX / 2) - 1
        self.assertEqual(self.character.needs.hunger_label(), "Well fed")

    def test_at_midpoint_is_hungry(self):
        self.character.needs.hunger = HUNGER_MAX / 2
        self.assertEqual(self.character.needs.hunger_label(), "Hungry")

    def test_above_midpoint_is_hungry(self):
        self.character.needs.hunger = HUNGER_MAX
        self.assertEqual(self.character.needs.hunger_label(), "Hungry")
