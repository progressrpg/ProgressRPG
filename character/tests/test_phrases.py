from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from character.phrases import generate_phrase, load_phrases


class CharacterPhrasesTests(SimpleTestCase):
    def setUp(self):
        load_phrases.cache_clear()

    def test_generate_phrase_replaces_character_placeholder(self):
        character = SimpleNamespace(first_name="Ari", name="Ari Stone")

        with patch(
            "character.phrases.random.choice", return_value="{character} keeps going."
        ):
            phrase = generate_phrase("stable", "work", character)

        self.assertEqual(phrase, "Ari keeps going.")

    def test_generate_phrase_falls_back_to_default_when_state_missing(self):
        character = SimpleNamespace(first_name="Ari", name="Ari Stone")

        phrase = generate_phrase("unknown_state", "work", character)

        self.assertEqual(phrase, "Ari completes a task.")

    def test_generate_phrase_falls_back_to_work_when_activity_missing(self):
        character = SimpleNamespace(first_name="Ari", name="Ari Stone")

        with patch(
            "character.phrases.random.choice", return_value="{character} handles it."
        ):
            phrase = generate_phrase("stable", "idle", character)

        self.assertEqual(phrase, "Ari handles it.")
