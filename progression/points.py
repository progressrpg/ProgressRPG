# progression/points.py
"""
Shared Activity Points (AP) / skill Experience Points (XP) formula.

AP is the universal currency earned for everything a character or player
does. XP is additionally earned per skill, for activities tied to one (see
SkillDefinition / CharacterSkill in progression.models). Both are derived
live from a record's `duration` plus the current formula/settings rather
than frozen at completion time, so balance changes can be recalculated
retroactively - see TimeRecord.reward_breakdown.

Owns the skill-XP base rate and mastery multiplier (base_rate,
xp_for_duration, xp_mastery_multiplier), used for per-skill XP and the AP
mastery bonus. For the level/AP curve and the online/activity-boost
multiplier lookup, see progression/ap.py instead.
"""

from decimal import Decimal
from typing import Any


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
    a character or player has become overall, the faster they earn AP on
    anything. Linear growth up to a configurable cap, both GameSettings-
    tunable. See progression.models.character_total_skill_xp/
    player_total_skill_xp for how `total_xp` is computed for each owner.
    """
    from core.models import GameSettings

    settings = GameSettings.current()
    growth = Decimal(total_xp) / settings.xp_mastery_scale
    return min(settings.xp_mastery_multiplier_cap, Decimal("1.0") + growth)


def format_reward_value(value: Decimal) -> int | float:
    """
    Render a Decimal for storage in a reward breakdown: whole values as ints,
    everything else as floats. `reward_breakdown` is a JSONField, so Decimals
    cannot go in as-is.
    """
    return int(value) if value == value.to_integral_value() else float(value)


def build_reward_summary(
    *,
    duration_seconds: int,
    base_xp: Decimal | int,
    multiplier: Decimal,
    skill_xp_gained: int,
    components: dict[str, Decimal] | None = None,
) -> dict[str, Any]:
    """
    Shared shape for the AP/XP breakdown that both PlayerActivity and
    CharacterActivity produce and store in `TimeRecord.reward_breakdown`.

    The two owners compute *different* multipliers - a player's is premium x
    task x mastery, a character's is kind x boost x mastery - so each passes
    its own already-composed `multiplier` plus its own named `components` for
    the itemised view. What this function owns is the part that must not
    drift: the common key set, the Decimal-to-JSON formatting, and the fact
    that `xp_gained` is computed from the unrounded values rather than from
    the formatted ones.

    Always present: duration_seconds, base_xp, xp_multiplier, xp_gained,
    skill_xp_gained. Owner-specific keys arrive via `components`.

    Keys may only ever be ADDED here. `reward_breakdown` rows are historical
    snapshots that are never backfilled, and the frontend reads `base_xp`,
    `xp_multiplier` and `task_xp_multiplier` by name - renaming or removing
    one silently breaks both.
    """
    base = Decimal(base_xp)

    summary: dict[str, Any] = {
        "duration_seconds": duration_seconds,
        "base_xp": format_reward_value(base),
        "xp_multiplier": format_reward_value(multiplier),
        "xp_gained": int(base * multiplier),
        "skill_xp_gained": skill_xp_gained,
    }

    for name, value in (components or {}).items():
        summary[name] = format_reward_value(value)

    return summary
