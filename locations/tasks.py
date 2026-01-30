from celery import shared_task
from django.core.management import call_command


@shared_task
def move_characters_tick(time_delta=1.0):
    from character.models import Character
    from .models import Journey

    movers = list(
        Character.objects.filter(is_moving=True).select_related(
            "current_node",
            "target_node",
        )
    )

    mover_ids = [c.id for c in movers]
    journeys = {
        j.character_id: j
        for j in Journey.objects.filter(character_id__in=mover_ids, status="active")
    }

    for char in movers:
        journey = journeys.get(char.id)
        if not journey:
            char.is_moving = False
            char.target_node = None
            continue

        char._journey = journey
        char.step_toward(time_delta)

    Character.objects.bulk_update(
        movers,
        (
            "location",
            "current_node",
            "target_node",
            "is_moving",
        ),
    )

    if Character.objects.filter(is_moving=True).exists():
        move_characters_tick.apply_async(countdown=time_delta)


@shared_task
def spawn_villages_task():
    call_command("spawn_villages")


@shared_task
def spawn_characters_task():
    call_command("spawn_characters")


@shared_task
def populate_interiors_task():
    call_command("populate_interiors")


@shared_task
def place_characters_task():
    call_command("place_characters")


@shared_task
def generate_landarea_task(overwrite=False):
    call_command("generate_landarea", overwrite=overwrite)
