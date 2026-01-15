# character/tasks.py
from celery import shared_task
from django.utils import timezone

from character.models import Character


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def generate_character_days(self, date_iso: str | None = None) -> dict:
    """
    Generate scheduled CharacterActivity rows for every character for the given date.
    If date_iso is None, uses localdate() (Europe/London).
    """
    target_date = (
        timezone.localdate()
        if not date_iso
        else timezone.datetime.fromisoformat(date_iso).date()
    )

    generated = 0
    skipped_no_behaviour = 0

    qs = Character.objects.select_related("behaviour").all()

    for character in qs:
        behaviour = getattr(character, "behaviour", None)
        if not behaviour:
            skipped_no_behaviour += 1
            continue

        # Your Behaviour.generate_day should be idempotent for that date
        behaviour.generate_day(target_date)
        generated += 1

    return {
        "date": str(target_date),
        "generated_for_characters": generated,
        "skipped_no_behaviour": skipped_no_behaviour,
    }
