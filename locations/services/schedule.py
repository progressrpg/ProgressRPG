from __future__ import annotations

import logging
from datetime import time

from django.utils import timezone

logger = logging.getLogger("general")

WORK_START = time(8, 0)
WORK_END = time(18, 0)

# Per-character transition boundaries are jittered by up to this many
# seconds either way, so the whole village doesn't flip home/work in lockstep.
MAX_STAGGER_SECONDS = 20 * 60

_UNSET = object()


def _stagger_offset_seconds(character_id: int) -> int:
    """Deterministic per-character offset in [-MAX_STAGGER_SECONDS, MAX_STAGGER_SECONDS]."""
    span = 2 * MAX_STAGGER_SECONDS + 1
    return (character_id % span) - MAX_STAGGER_SECONDS


def work_hours_for(character, work_location=_UNSET) -> tuple[time, time]:
    """The (open, close) window a character should be at work, from their
    assigned work building's open_time/close_time if set, else the fixed
    WORK_START/WORK_END constants. Shared by target_role_for (drives
    physical movement) and behaviour_services.generate_day (drives the
    scheduled CharacterActivity blocks), so a character's actual work
    building's hours - e.g. an inn open until 23:00 - govern both rather
    than generate_day assuming a fixed 8-17 workday that leaves late
    building hours showing as an unrelated leisure/"Relaxing" block.

    `work_location` may be passed in pre-fetched (e.g. by a caller batching
    lookups across many characters, such as commute_tick) to avoid a
    per-character query. Left unset, it's looked up here as before.
    """
    from character.models import CharacterLocation

    work_start, work_end = WORK_START, WORK_END
    if work_location is _UNSET:
        work_location = (
            CharacterLocation.objects.filter(
                character=character, role=CharacterLocation.Role.WORK, is_primary=True
            )
            .select_related("location")
            .first()
        )
    if work_location is not None:
        building = work_location.location
        if building.open_time is not None and building.close_time is not None:
            work_start, work_end = building.open_time, building.close_time
    return work_start, work_end


def target_role_for(character, now=None, work_location=_UNSET) -> str:
    """Which role (home/work) a character should currently be at.

    The work window comes from the character's assigned work building's
    open_time/close_time if set, else falls back to the fixed WORK_START/
    WORK_END constants. A per-character stagger is applied to whichever
    window is resolved, so the whole village doesn't flip in lockstep.

    `work_location` is forwarded to work_hours_for - see its docstring.
    """
    from character.models import CharacterLocation

    now = now or timezone.localtime()
    seconds_since_midnight = now.hour * 3600 + now.minute * 60 + now.second

    work_start, work_end = work_hours_for(character, work_location=work_location)

    offset = _stagger_offset_seconds(character.id)
    work_start_seconds = work_start.hour * 3600 + work_start.minute * 60 + offset
    work_end_seconds = work_end.hour * 3600 + work_end.minute * 60 + offset

    if work_start_seconds <= seconds_since_midnight < work_end_seconds:
        return CharacterLocation.Role.WORK
    return CharacterLocation.Role.HOME


def sync_character_location(
    character, target_role=_UNSET, target_location=_UNSET, entrance_node=_UNSET
) -> None:
    """Compare a character's current/target position against their schedule
    and, if they should be elsewhere, send them there via the existing
    Journey/set_destination movement stack. No-op if already there, already
    heading there, mid-journey, or no matching CharacterLocation/path exists.

    `target_role`, `target_location`, and `entrance_node` may be passed in
    pre-fetched (e.g. by a caller batching lookups across many characters,
    such as commute_tick) to avoid a per-character query. Left unset,
    they're looked up here as before.
    """
    from character.models import CharacterLocation
    from locations.models import Node

    if character.is_moving:
        return

    if target_role is _UNSET:
        target_role = target_role_for(character)

    if target_location is _UNSET:
        target_location = (
            CharacterLocation.objects.filter(
                character=character, role=target_role, is_primary=True
            )
            .select_related("location")
            .first()
        )
    if target_location is None:
        return

    if entrance_node is _UNSET:
        entrance_node = Node.objects.filter(
            building=target_location.location, kind=Node.Kind.BUILDING_ENTRANCE
        ).first()
    if entrance_node is None:
        return

    if character.current_node_id == entrance_node.id:
        return
    if character.target_node_id == entrance_node.id:
        return

    try:
        character.set_destination(node=entrance_node)
    except ValueError:
        logger.info(
            "sync_character_location: could not route character %s to %s (%s)",
            character.id,
            target_location.location,
            target_role,
        )
