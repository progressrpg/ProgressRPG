import itertools
import random
import time

from celery import shared_task
from django.core.cache import cache
from django.core.management import call_command

# Nominal real-world cadence the self-rescheduling tick loop aims for.
# Celery's `countdown` is only a lower bound on the delay before a task is
# *eligible* to run, not a guarantee of when it actually runs - broker/worker
# load can push the real gap between ticks past this. move_characters_tick
# measures that real gap itself (see time_delta below) rather than assuming
# it's always exactly this value, so simulated movement stays in step with
# real elapsed time - which is what the frontend's between-poll walker
# animation assumes (see issue #624: server/client disagreeing about how far
# a character should have moved surfaced as a visible correction, in sync
# across every moving character, roughly every poll).
MOVE_TICK_NOMINAL_SECONDS = 1.0
# Ceiling on how much elapsed real time a single tick will credit as
# movement, so a long stall (worker restart, deploy, broker backlog) doesn't
# let characters teleport once ticking resumes - they just take a few more,
# still real-time-accurate, ticks to catch up.
MOVE_TICK_MAX_SECONDS = 5.0

_LAST_TICK_CACHE_KEY = "locations:move_characters_tick:last_run_at"


def _chunked(iterable, size):
    it = iter(iterable)
    while chunk := list(itertools.islice(it, size)):
        yield chunk


@shared_task
def move_characters_tick(time_delta=None):
    """Process character movement in batches. Avoid loading all movers into memory."""
    from character.models import Character
    from .models import Journey, Node

    now = time.time()
    if time_delta is None:
        last_run_at = cache.get(_LAST_TICK_CACHE_KEY)
        time_delta = (
            min(now - last_run_at, MOVE_TICK_MAX_SECONDS)
            if last_run_at is not None
            else MOVE_TICK_NOMINAL_SECONDS
        )
    cache.set(_LAST_TICK_CACHE_KEY, now, timeout=None)

    batch_size = 100

    movers_qs = (
        Character.objects.filter(is_moving=True)
        .select_related("current_node", "target_node")
        .iterator(chunk_size=batch_size)
    )

    for chars in _chunked(movers_qs, batch_size):
        journeys_by_character = {
            journey.character_id: journey
            for journey in Journey.objects.filter(
                character_id__in=[char.id for char in chars], status="active"
            ).select_related("destination_node")
        }

        node_ids = {
            node_id
            for journey in journeys_by_character.values()
            if journey.path_nodes
            for node_id in journey.path_nodes
        }
        node_cache = Node.objects.in_bulk(node_ids)

        for char in chars:
            journey = journeys_by_character.get(char.id)

            if not journey:
                char.is_moving = False
                char.target_node = None
            else:
                journey._node_cache = node_cache
                char._journey = journey
                char.step_toward(time_delta)

        Character.objects.bulk_update(
            chars,
            (
                "location",
                "current_node",
                "target_node",
                "is_moving",
            ),
        )

    # Check if there are still moving characters. Reschedule at the nominal
    # cadence, not `time_delta` - `time_delta` is how much time this tick
    # measured as *having already elapsed*, not how long to wait next.
    if Character.objects.filter(is_moving=True).exists():
        move_characters_tick.apply_async(countdown=MOVE_TICK_NOMINAL_SECONDS)


@shared_task
def wander_tick(fraction=0.2):
    """
    Decorative-only movement for the village view: each tick, nudges a random
    subset of idle characters within their village boundary (linked or not -
    this is purely visual, not tied to gameplay). Deliberately independent of
    move_characters_tick/Journey - does not touch is_moving/current_node, so
    it can't interfere with the travel/pathfinding system. Only a subgroup
    moves per tick so the whole village doesn't shuffle in lockstep.
    """
    from character.models import Character
    from .services.wander import wander

    candidate_ids = list(
        Character.objects.filter(
            is_moving=False, population_centre__isnull=False
        ).values_list("id", flat=True)
    )
    if not candidate_ids:
        return

    sample_size = max(1, round(len(candidate_ids) * fraction))
    chosen_ids = random.sample(candidate_ids, min(sample_size, len(candidate_ids)))

    for character in Character.objects.filter(id__in=chosen_ids).select_related(
        "population_centre"
    ):
        wander(character)


@shared_task
def commute_tick():
    """
    Sweep idle, village-assigned characters and send anyone who should be
    home/at work but isn't (and isn't already heading there) via the
    existing Journey/set_destination movement stack. Replaces wander_tick
    as the scheduled beat task - see locations.services.schedule.
    """
    from character.models import Character, CharacterLocation
    from .models import Node
    from .services.schedule import sync_character_location, target_role_for

    characters = list(
        Character.objects.filter(
            is_moving=False, population_centre__isnull=False
        ).select_related("current_node", "target_node")
    )
    if not characters:
        return

    # Batch every character's primary locations (home + work) in one query,
    # rather than letting target_role_for's work_hours_for lookup issue its
    # own per-character CharacterLocation query in the loop below (was an
    # N+1 flagged by Sentry).
    primary_locations = list(
        CharacterLocation.objects.filter(
            character_id__in=[character.id for character in characters],
            is_primary=True,
        ).select_related("location")
    )
    work_locations_by_character = {
        char_location.character_id: char_location
        for char_location in primary_locations
        if char_location.role == CharacterLocation.Role.WORK
    }

    target_roles = {
        character.id: target_role_for(
            character, work_location=work_locations_by_character.get(character.id)
        )
        for character in characters
    }

    target_locations = {
        char_location.character_id: char_location
        for char_location in primary_locations
        if char_location.role == target_roles[char_location.character_id]
    }

    entrance_nodes_by_building = {
        node.building_id: node
        for node in Node.objects.filter(
            building_id__in={
                char_location.location_id for char_location in target_locations.values()
            },
            kind=Node.Kind.BUILDING_ENTRANCE,
        )
    }

    for character in characters:
        target_location = target_locations.get(character.id)
        entrance_node = (
            entrance_nodes_by_building.get(target_location.location_id)
            if target_location is not None
            else None
        )
        sync_character_location(
            character,
            target_role=target_roles[character.id],
            target_location=target_location,
            entrance_node=entrance_node,
        )


@shared_task
def generate_villages_task():
    call_command("generate_villages")


@shared_task
def generate_characters_task():
    call_command("generate_characters")


@shared_task
def populate_interiors_task():
    call_command("populate_interiors")


@shared_task
def place_characters_task():
    call_command("place_characters")


@shared_task
def generate_landarea_task(overwrite=False):
    call_command("generate_landarea", overwrite=overwrite)
