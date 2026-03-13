import json
import logging
import random
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger("general")
PHRASES_PATH = Path(__file__).resolve().parent / "data" / "phrases.json"


@lru_cache(maxsize=1)
def load_phrases():
    try:
        with PHRASES_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.warning("[CHAR.PHRASES] Phrases file not found: %s", PHRASES_PATH)
        return {}
    except json.JSONDecodeError as exc:
        logger.warning("[CHAR.PHRASES] Invalid phrases JSON: %s", exc)
        return {}

    if not isinstance(data, dict):
        logger.warning("[CHAR.PHRASES] Root JSON must be an object.")
        return {}

    return data


def _character_name(character):
    if getattr(character, "first_name", None):
        return character.first_name
    if getattr(character, "name", None):
        return character.name
    return "Your companion"


def generate_phrase(state, activity_type, character):
    phrases = load_phrases()
    name = _character_name(character)

    state_key = (state or "").strip().lower()
    state_block = phrases.get(state_key, {})
    if not isinstance(state_block, dict):
        return f"{name} completes a task."

    activity_key = (activity_type or "").strip().lower()
    activity_phrases = state_block.get(activity_key)

    if not isinstance(activity_phrases, list) or not activity_phrases:
        activity_phrases = state_block.get("work")

    if not isinstance(activity_phrases, list) or not activity_phrases:
        return f"{name} completes a task."

    template = random.choice(activity_phrases)
    if not isinstance(template, str):
        return f"{name} completes a task."

    try:
        return template.format(character=name)
    except Exception:
        logger.warning("[CHAR.PHRASES] Failed to format phrase template: %s", template)
        return template.replace("{character}", name)
