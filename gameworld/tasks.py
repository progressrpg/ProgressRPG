from celery import shared_task
from zoneinfo import ZoneInfo
from django.utils import timezone
from datetime import date, datetime, timedelta
from astral import LocationInfo
from astral.sun import sun
import random


from .models import DailySunTimes, GameWorld
from character.models import Character


@shared_task
def precompute_sun_times(days_ahead=7):
    world = GameWorld.get_instance()
    tz = ZoneInfo(world.timezone)
    today = date.today()

    for delta in range(days_ahead):
        target_date = today + timedelta(days=delta)
        loc = LocationInfo(latitude=world.latitude, longitude=world.longitude)
        s = sun(loc.observer, date=target_date, tzinfo=tz)

        DailySunTimes.objects.update_or_create(
            world=world,
            date=target_date,
            defaults={
                "sunrise": s["sunrise"],
                "sunset": s["sunset"],
                "dawn": s["dawn"],
                "dusk": s["dusk"],
            },
        )


@shared_task
def sun_phase_started(phase):
    """
    Notify characters/world that a sun phase has started.
    Uses iterator() to avoid loading all characters into memory.
    """
    from character.models import Character

    print(f"Sun phase started: {phase}")

    # Process characters in batches to avoid memory overload
    batch_size = 100
    for char in Character.objects.iterator(chunk_size=batch_size):
        char.react_to_sun_phase(phase)


def schedule_sun_phase_tasks():
    """
    Call this after precomputing sun times to schedule today's phase events
    """
    world = GameWorld.get_instance()
    now = datetime.now().astimezone()
    today_times = world.sun_times.get(date=now.date())

    phases = [
        ("dawn", today_times.dawn),
        ("day", today_times.sunrise),
        ("dusk", today_times.dusk),
        ("night", today_times.sunset),
    ]

    for phase_name, phase_time in phases:
        delta_seconds = (phase_time - now).total_seconds()
        if delta_seconds > 0:
            sun_phase_started.apply_async(countdown=delta_seconds, args=[phase_name])


def death_probability(age):
    """Calculate daily death probability based on age"""
    if age < 60:
        return 0
    return ((age - 60) ** 2) / 10000


@shared_task
def check_character_deaths():
    """Daily check to determine if NPCs die based on age.
    Uses iterator() to process in batches."""
    death_count = 0
    batch_size = 100

    # Process characters in batches to avoid memory overload
    for character in Character.objects.iterator(chunk_size=batch_size):
        age = timezone.now().date() - character.birth_date
        chance = death_probability(age)

        if random.random() < chance:
            character.die()
            death_count += 1

    print(f"{death_count} people died of old age today.")


@shared_task
def check_character_pregnancies():
    """Check pregnancies and schedule births. Uses iterator() for memory efficiency."""
    today = timezone.now().date()
    batch_size = 100

    # Process pregnant characters in batches
    for character in Character.objects.filter(is_pregnant=True).iterator(
        chunk_size=batch_size
    ):
        pregnancy_duration = (today - character.pregnancy_start_date).days

        if pregnancy_duration >= 260:
            # Pick a random day in following week for birth
            birth_day = today + timezone.timedelta(days=random.randint(7, 13))
            # Pick a random time for birthday
            random_hour = random.randint(0, 23)
            random_minute = random.randint(0, 59)
            random_second = random.randint(0, 59)
            character.pregnancy_due_date = timezone.make_aware(
                timezone.datetime.combine(
                    birth_day, timezone.time(random_hour, random_minute, random_second)
                )
            )
            handle_birth.apply_async((character.id), eta=character.pregnancy_due_date)
        if random() < character.get_miscarriage_chance():
            character.handle_miscarriage()


@shared_task
def handle_birth(character_id):
    character = Character.objects.get(id=character_id)
    if character:
        character.handle_childbirth()
