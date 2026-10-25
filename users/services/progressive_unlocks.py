"""
Progression-gated UI unlocks for new signups (issue #549).

New players see only the Timer at first; the Infobar, Library page, and Map
unlock as they reach progression milestones (1st activity, 2nd activity,
level 4 respectively). Existing ("legacy") players — those created before
`GameSettings.progressive_unlocks_enabled_from` — are unaffected: they
always see everything and never get the new-unlock tutorial popups.

Two questions are deliberately kept separate:

- `unlock_visible`: should the UI element be shown right now? Always True
  for legacy players.
- `new_signup_milestone_reached`: should the TutorialStep introducing that
  element pop up? Always False for legacy players, even though the element
  itself is always visible to them - conflating the two would either show
  the new-feature modal to players who've had the feature all along, or
  hide UI legacy players are entitled to.
"""

from core.models import GameSettings

INFOBAR = "infobar"
LIBRARY = "library"
MAP = "map"

_ACTIVITY_THRESHOLDS = {
    INFOBAR: 1,
    LIBRARY: 2,
}


def is_new_signup(player) -> bool:
    """Whether this player is subject to progressive-unlock gating at all."""
    cutoff = GameSettings.current().progressive_unlocks_enabled_from
    return player.created_at >= cutoff


def milestone_reached(player, key: str) -> bool:
    """
    Whether the progression milestone for `key` has been reached, ignoring
    the new-signup cohort check entirely.
    """
    if key == MAP:
        return player.level >= 4
    threshold = _ACTIVITY_THRESHOLDS[key]
    return player.total_activities >= threshold


def unlock_visible(player, key: str) -> bool:
    """Should this UI element be shown to this player right now?"""
    if not is_new_signup(player):
        return True
    return milestone_reached(player, key)


def new_signup_milestone_reached(player, key: str) -> bool:
    """Should the TutorialStep introducing this element pop up for them?"""
    if not is_new_signup(player):
        return False
    return milestone_reached(player, key)
