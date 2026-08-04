# progression/points.py
"""
Shared Activity Points (AP) / skill Experience Points (XP) formula.

AP is the universal currency earned for everything a character or player
does. XP is additionally earned per skill, for activities tied to one (see
SkillDefinition / CharacterSkill in progression.models). Both are derived
live from a record's `duration` plus the current formula/settings rather
than frozen at completion time, so balance changes can be recalculated
retroactively - see TimeRecord.reward_breakdown.
"""

from decimal import Decimal


def base_rate() -> Decimal:
    from core.models import GameSettings

    return GameSettings.current().default_activity_xp_per_second


def xp_for_duration(duration_seconds) -> int:
    """
    Skill XP earned for `duration_seconds` of completed skill-tied work -
    the flat, unscaled base rate. Unlike AP, XP is not scaled by the mastery
    multiplier (that would make it self-referential).
    """
    return int(Decimal(duration_seconds) * base_rate())


def xp_mastery_multiplier(total_xp) -> Decimal:
    """
    AP-earning multiplier driven by accumulated skill XP - the more skilled
    a character has become overall, the faster they earn AP on anything.
    Linear growth up to a configurable cap, both GameSettings-tunable.
    Players have no skill XP source yet, so `total_xp=0` here always
    resolves to 1.0 (no boost) until a player-side skill system exists.
    """
    from core.models import GameSettings

    settings = GameSettings.current()
    growth = Decimal(total_xp) / settings.xp_mastery_scale
    return min(settings.xp_mastery_multiplier_cap, Decimal("1.0") + growth)
