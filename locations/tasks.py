from celery import shared_task
from django.core.management import call_command


@shared_task
def move_characters_tick(time_delta=1.0):
    """Process character movement in batches. Avoid loading all movers into memory."""
    from character.models import Character
    from .models import Journey

    batch_size = 100
    movers_to_update = []
    has_more_movers = False

    # Process movers in batches to avoid memory overload
    for char in (
        Character.objects.filter(is_moving=True)
        .select_related(
            "current_node",
            "target_node",
        )
        .iterator(chunk_size=batch_size)
    ):
        # Check if there's an active journey for this character
        journey = Journey.objects.filter(character_id=char.id, status="active").first()

        if not journey:
            char.is_moving = False
            char.target_node = None
        else:
            char._journey = journey
            char.step_toward(time_delta)

        movers_to_update.append(char)

        # Bulk update in batches to avoid memory accumulation
        if len(movers_to_update) >= batch_size:
            Character.objects.bulk_update(
                movers_to_update,
                (
                    "location",
                    "current_node",
                    "target_node",
                    "is_moving",
                ),
            )
            movers_to_update = []

    # Update any remaining movers
    if movers_to_update:
        Character.objects.bulk_update(
            movers_to_update,
            (
                "location",
                "current_node",
                "target_node",
                "is_moving",
            ),
        )

    # Check if there are still moving characters
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
