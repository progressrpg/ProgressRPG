from django.contrib.gis.geos import Point
from django.test import TestCase

from character.models import Character
from character.tasks import generate_character_days
from progression.models import CharacterActivity


class GenerateCharacterDaysTaskTests(TestCase):
    def test_generates_activities_for_characters_with_behaviour(self):
        character = Character.objects.create(
            first_name="Genny", location=Point(0, 0, srid=3857)
        )

        result = generate_character_days(date_iso="2026-01-05")

        self.assertEqual(result["generated_for_characters"], 1)
        self.assertEqual(result["skipped_no_behaviour"], 0)
        self.assertTrue(CharacterActivity.objects.filter(character=character).exists())

    def test_skips_characters_without_behaviour(self):
        character = Character.objects.create(
            first_name="NoBehaviour", location=Point(0, 0, srid=3857)
        )
        character.behaviour.delete()

        result = generate_character_days(date_iso="2026-01-06")

        self.assertEqual(result["generated_for_characters"], 0)
        self.assertEqual(result["skipped_no_behaviour"], 1)
