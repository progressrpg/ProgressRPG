# progression/ap.py
"""
Activity Points (AP) - the universal, level-driving currency shared by
Player and Character. Extracted so the level-up curve and multiplier lookup
have one clearly-named home, independent of where the running total ends up
being stored.

This is Phase 1 of the progression-track migration in
.claude/plans/progression-track-abstraction.md: a same-file extraction with
no schema change. Player and Character still own the `xp`/`level`/
`xp_next_level` columns and still do the actual reads/writes/saves - these
functions only carry the pure curve math and the multiplier query, with a
method surface (`apply_xp` returning a new level/xp/levelups; a total-earned
reconstruction; a multiplier lookup) that a future ProgressionTrack model
can adopt directly without every caller (Player.add_xp, Character.add_xp,
total_ap_earned, get_xp_multiplier) having to change twice.
"""

from decimal import Decimal
from typing import Any

from django.db import models
from django.utils import timezone


def threshold_for_level(level: int) -> int:
    """AP required to advance from `level` to `level + 1`."""
    return 100 * (level + 1)


def total_ap_earned(level: int, xp: int) -> int:
    """
    Reconstruct the monotonic lifetime AP total from a level plus the
    current xp-toward-next-level remainder. Level-up thresholds are
    cumulative, so unlike `xp` (which resets on every level-up) this stays
    monotonic - used wherever a long-term progress/prestige figure is
    needed, e.g. village points.
    """
    thresholds_cleared = sum(threshold_for_level(lvl) for lvl in range(level))
    return thresholds_cleared + xp


def apply_xp(level: int, xp: int, amount: int) -> tuple[int, int, list[dict[str, Any]]]:
    """
    Apply `amount` AP on top of (level, xp) and run the level-up loop.

    Returns (new_level, new_xp, levelups), where levelups is a list of
    {"old_level", "new_level"} dicts, oldest first, one per level gained.
    """
    xp += amount
    levelups = []

    while True:
        xp_needed = threshold_for_level(level)
        if xp < xp_needed:
            break

        old_level = level
        xp -= xp_needed
        level += 1
        levelups.append({"old_level": old_level, "new_level": level})

    return level, max(0, xp), levelups


def get_multiplier(person, now=None) -> Decimal:
    """
    Combined XpModifier multiplier for `person` (a Player or Character) -
    both provide a `xp_mods` reverse manager (see gameplay.models.XpModifier).

    Modifiers combine in two buckets:

        total = (1 + sum of additive bonuses) * product of multiplicative ones

    A modifier's value always reads as "+X%" - 1.25 means +25% - and its
    `stacking` mode decides which bucket that 25% lands in. Two additive
    +25% modifiers give 1.5; two multiplicative ones give 1.5625.

    Order is deliberately irrelevant: addition commutes within the bucket and
    multiplication commutes across the two, so there is no precedence to
    define and none to get wrong when a modifier is added later.

    There is no cap. The multipliers are a small authored set, and the
    additive bucket already bounds the growth that would otherwise motivate
    one. If a ceiling is ever wanted it belongs in GameSettings, alongside
    xp_mastery_multiplier_cap, rather than hardcoded here.

    Note that the stacked case is the *normal* case, not an edge case: a
    player who is actively recording is by definition also online, so
    player_online and activity_active are both live during ordinary engaged
    play.
    """
    now = now or timezone.now()

    from gameplay.models import XpModifier

    mods = person.xp_mods.filter(
        is_active=True,
        starts_at__lte=now,
    ).filter(models.Q(ends_at__isnull=True) | models.Q(ends_at__gt=now))

    additive_bonus = Decimal("0")
    multiplicative = Decimal("1.0")

    for mod in mods:
        if mod.stacking == XpModifier.Stacking.ADDITIVE:
            additive_bonus += mod.multiplier - Decimal("1")
        else:
            multiplicative *= mod.multiplier

    return (Decimal("1.0") + additive_bonus) * multiplicative


# Authored baseline productivity for every character - flat for v1, may
# later factor in role/mood/history (see issue #750).
CHARACTER_BASELINE_PRODUCTIVITY = Decimal("1.0")


def get_productivity(character, now=None) -> Decimal:
    """
    Live "how productive is this character right now" signal: the authored
    baseline times whatever XpModifier multiplier is currently active on the
    character (player-online / player-actively-timing boosts - see
    gameplay.services.xp_modifiers).

    Deliberately not derived from lifetime AP total - an old character
    accumulates AP over a long life regardless of whether a player is
    currently engaged with it, which would read as misleadingly
    "productive". Reading live modifier state instead gives instant
    feedback: productivity moves the moment a boost activates or clears, no
    averaging/smoothing/lag.
    """
    return CHARACTER_BASELINE_PRODUCTIVITY * get_multiplier(character, now=now)
