# progression/ap.py
"""
Activity Points (AP) - the universal, level-driving currency shared by
Player and Character (see users.models.Person). Extracted out of Person so
the level-up curve and multiplier lookup have one clearly-named home,
independent of where the running total ends up being stored.

This is Phase 1 of the progression-track migration in
.claude/plans/progression-track-abstraction.md: a same-file extraction with
no schema change. Person still owns the `xp`/`level`/`xp_next_level` columns
and still does the actual reads/writes/saves - these functions only carry
the pure curve math and the multiplier query, with a method surface
(`apply_xp` returning a new level/xp/levelups; a total-earned reconstruction;
a multiplier lookup) that a future ProgressionTrack model can adopt directly
without every caller (Person.add_xp, total_ap_earned, get_xp_multiplier)
having to change twice.
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
    Active XpModifier multiplier for `person` (a Player or Character) - both
    provide a `xp_mods` reverse manager (see gameplay.models.XpModifier).
    """
    now = now or timezone.now()

    mods = person.xp_mods.filter(
        is_active=True,
        starts_at__lte=now,
    ).filter(models.Q(ends_at__isnull=True) | models.Q(ends_at__gt=now))
    mult = Decimal("1.0")
    for m in mods:
        mult *= m.multiplier

    return mult
