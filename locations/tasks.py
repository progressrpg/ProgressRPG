from celery import shared_task
from character.models import Character
from django.db import transaction


@shared_task
def move_characters_tick(time_delta=5.0):
    movables = Character.objects.filter(target_location__isnull=False)

    updated = []

    for obj in movables:
        changed = obj.step_toward(time_delta=time_delta)
        if changed:
            updated.append(obj)

    if updated:
        with transaction.atomic():
            Character.objects.bulk_update(
                updated, ("location", "target_location", "is_moving")
            )

    return updated
