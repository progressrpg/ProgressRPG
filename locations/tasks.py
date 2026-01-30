from celery import shared_task
from django.core.management import call_command


@shared_task
def move_characters_tick(time_delta=1.0):
    from character.models import Character

    movers = Character.objects.filter(is_moving=True).select_related(
        "current_node",
        "target_node",
    )

    if not movers.exists():
        return

    for char in movers:
        changed = char.step_toward(time_delta)

    Character.objects.bulk_update(
        movers,
        (
            "location",
            "current_node",
            "target_node",
            "is_moving",
            "current_content_type",
            "current_object_id",
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
