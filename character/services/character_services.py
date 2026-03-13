from __future__ import annotations

import logging

from django.db import transaction

from progress_rpg.exceptions import QuestError

logger = logging.getLogger("general")
logger_errors = logging.getLogger("errors")


def character_react_to_sun_phase(character, phase: str) -> None:
    if phase == "dawn":
        print(f"{character.name} wakes up and moves outside")
        character.go_outside(radius=10)
    elif phase == "day":
        print(f"{character.name} is outside during the day")
    elif phase == "dusk":
        print(f"{character.name} heads inside for the night")
        character.go_home()
    elif phase == "night":
        print(f"{character.name} is indoors at night")


def character_assign_home(character, building) -> None:
    character.building = building
    character.population_centre = building.population_centre
    character.save(update_fields=["building", "population_centre"])


@transaction.atomic
def character_complete_quest(character, xp_gained):
    logger.info(f"[CHAR.COMPLETE_QUEST] Starting quest completion for {character}")

    quest = character.quest_timer.quest

    if quest is None:
        logger_errors.error(
            f"[CHAR.COMPLETE_QUEST] Quest is None for character {character.id}",
            extra={"character_id": character.id},
        )
        raise QuestError(f"No quest found for character {character.id}")

    rewards_summary = None
    try:
        if hasattr(quest, "results") and quest.results is not None:
            rewards_summary = character_apply_quest_results(character, quest)
        else:
            rewards_summary = {
                "xp_gained": 0,
                "coins_gained": 0,
                "dynamic_rewards": {},
                "levelups": [],
            }
    except Exception as e:
        logger_errors.exception(
            f"[CHAR.COMPLETE_QUEST] Error applying rewards for quest {quest.id}: {e}"
        )

    logger.info(f"[CHAR.COMPLETE_QUEST] Quest completion successful")
    return rewards_summary


@transaction.atomic
def character_apply_quest_results(character, quest):
    logger.info(f"[QUESTRESULTS.APPLY] Applying results to character {character.name}")
    results = getattr(quest, "results", {}) or {}

    xp_rate = getattr(results, "xp_rate", 1)

    time_xp = xp_rate * getattr(quest, "duration", 0)
    level_scaling = 1
    repeat_penalty = 1
    final_xp = time_xp * level_scaling * repeat_penalty

    coins_gained = results.get("coin_reward", 0)
    if coins_gained:
        character.get_currency("coins").earn(coins_gained)

    dynamic_rewards = results.get("dynamic_rewards", {})
    if dynamic_rewards:
        for key, value in dynamic_rewards.items():
            if hasattr(character, f"apply_{key}"):
                getattr(character, f"apply_{key}")(value)
            elif hasattr(character, key):
                current_value = getattr(character, key)
                if isinstance(current_value, (int, float)):
                    setattr(character, key, current_value + value)
                else:
                    setattr(character, key, value)
    else:
        logger.info("[CHAR.APPLY_QUEST_RESULTS] No dynamic rewards found for quest.")

    levelups = []
    try:
        levelups = character.add_xp(final_xp)

    except Exception as e:
        logger.exception(
            f"[CHAR.APPLY_QUEST_RESULTS] Error updating XP or quest count for character {character.id}: {e}"
        )
        return None

    try:
        from gameplay.models import ServerMessage

        for event in levelups:
            ServerMessage.objects.create(
                group=character.current_player.group_name,
                type="notification",
                action="notification",
                message=f"Character {character.name} levelled up! Now level {event['new_level']}.",
                data={"level": event["new_level"]},
                is_draft=False,
            )
    except Exception as e:
        logger.exception(
            f"[CHAR.COMPLETE_QUEST] Error notifying levelup for character {character.id}: {e}"
        )
        return None
    rewards_summary = {
        "xp_gained": final_xp if "final_xp" in locals() else 0,
        "coins_gained": getattr(results, "coin_reward", 0) if results else 0,
        "dynamic_rewards": (getattr(results, "dynamic_rewards", {}) if results else {}),
        "levelups": (
            [{"new_level": e["new_level"]} for e in levelups]
            if "levelups" in locals()
            else []
        ),
    }

    return rewards_summary


def character_has_available(model_cls) -> bool:
    return (
        model_cls.objects.filter(can_link=True).exclude(links__is_active=True).exists()
    )
