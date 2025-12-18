# progression/utils.py

from .models import CharacterQuest

from character.models import Character
from gameplay.models import Quest


def copy_quest(character: Character, quest: Quest):
    """
    Create a CharacterQuest instance from a Quest for a given character.

    Copies narrative fields (intro/outro), description, stages, and stage
    behaviour.
    """
    char_quest = CharacterQuest.objects.create(
        character=character,
        name=quest.name,
        description=quest.description,
        intro_text=quest.intro_text,
        outro_text=quest.outro_text,
        stages=quest.stages,
        stages_fixed=quest.stages_fixed,
        # Player chooses duration later; leave at default
        target_duration=0,
        duration=0,
    )

    char_quest.results = {
        "coin_reward": getattr(quest, "coin_reward", 0),
        "xp_rate": getattr(quest, "xp_rate", 0),
        "dynamic_rewards": getattr(quest, "dynamic_rewards", {}),
    }
    char_quest.save()

    return char_quest
