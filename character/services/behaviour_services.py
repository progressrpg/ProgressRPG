from __future__ import annotations

import random
from datetime import datetime, time, timedelta

from django.db import transaction
from django.utils import timezone

from character.utils import WORK_ACTIVITIES
from progression.models import CharacterActivity


def day_window(behaviour, date):
    tz = timezone.get_current_timezone()

    dawn_naive = datetime.combine(date, behaviour.DAWN_TIME)
    dusk_naive = datetime.combine(date, behaviour.DUSK_TIME)
    next_dawn_naive = datetime.combine(date + timedelta(days=1), behaviour.DAWN_TIME)

    dawn = timezone.make_aware(dawn_naive, tz)
    dusk = timezone.make_aware(dusk_naive, tz)
    next_dawn = timezone.make_aware(next_dawn_naive, tz)
    return dawn, dusk, next_dawn


@transaction.atomic
def generate_day(behaviour, date, replace_future=True):
    tz = timezone.get_current_timezone()

    rng = random.Random(f"{behaviour.character_id}-{date.isoformat()}")

    def aware(dt_date, t: time):
        return timezone.make_aware(datetime.combine(dt_date, t), tz)

    def jitter_minutes(base_dt, minutes):
        return base_dt + timedelta(minutes=rng.randint(-minutes, minutes))

    sleep_start = aware(date, time(23, 0))
    wake = aware(date, time(7, 0))
    wake = jitter_minutes(wake, 15)

    morning_start = wake
    morning_end = morning_start + timedelta(hours=1)

    work1_start = morning_end
    work1_end = aware(date, time(12, 0))

    lunch_start = work1_end
    lunch_start = jitter_minutes(lunch_start, 10)
    lunch_end = lunch_start + timedelta(hours=1)

    work2_start = lunch_end
    work2_end = aware(date, time(17, 0))

    dinner_start = aware(date, time(17, 30))
    dinner_start = jitter_minutes(dinner_start, 10)
    dinner_end = dinner_start + timedelta(hours=1)

    leisure_start = dinner_end
    leisure_end = aware(date, time(22, 30))

    wind_start = leisure_end
    wind_end = aware(date, time(23, 0))

    day_window(behaviour, date)

    next_day = date + timedelta(days=1)
    next_wake = aware(next_day, time(7, 0))
    next_wake = jitter_minutes(next_wake, 15)

    sleep_start = aware(date, time(23, 0))
    sleep_end = next_wake

    activities = random.sample(WORK_ACTIVITIES, 2)
    blocks = [
        ("sleep", "Sleeping", aware(date, time(0, 0)), morning_start),
        ("morning", "Waking up", morning_start, morning_end),
        ("work", activities[0], work1_start, work1_end),
        ("meal", "Eating lunch", lunch_start, lunch_end),
        ("work", activities[1], work2_start, work2_end),
        ("meal", "Eating dinner", dinner_start, dinner_end),
        ("leisure", "Relaxing", leisure_start, leisure_end),
        ("wind_down", "Winding down", wind_start, wind_end),
        ("sleep", "Sleeping", sleep_start, sleep_end),
    ]

    cleaned = []
    last_end = None
    for kind, name, start, end in blocks:
        if end <= start:
            continue
        if last_end and start < last_end:
            start = last_end
            if end <= start:
                continue
        cleaned.append((kind, name, start, end))
        last_end = end

    qs = CharacterActivity.objects.select_for_update().filter(
        character=behaviour.character
    )

    if replace_future:
        window_start = aware(date, time(0, 0))
        window_end = aware(date, time(23, 59, 59))
        qs.filter(
            is_complete=False,
            scheduled_start__lt=sleep_end,
            scheduled_end__gt=window_start,
        ).delete()

    created = []
    today = timezone.now().date()
    is_past = date < today

    for kind, name, start, end in cleaned:
        activity_kwargs = {
            "character": behaviour.character,
            "kind": kind,
            "name": name,
            "scheduled_start": start,
            "scheduled_end": end,
        }
        if is_past:
            activity_kwargs.update(
                {
                    "is_complete": True,
                    "started_at": start,
                    "completed_at": end,
                    "duration": int((end - start).total_seconds()),
                }
            )
        created.append(CharacterActivity.objects.create(**activity_kwargs))

    return created


@transaction.atomic
def sync_to_now(behaviour, now=None):
    now = now or timezone.now()

    qs = (
        CharacterActivity.objects.select_for_update()
        .filter(character=behaviour.character)
        .exclude(scheduled_start__isnull=True)
        .exclude(scheduled_end__isnull=True)
    )

    ended = qs.filter(is_complete=False, scheduled_end__lte=now).order_by(
        "scheduled_end"
    )
    for activity in ended:
        activity.complete_past()

    current = get_current_activity(behaviour)

    if current:
        if current.started_at is None:
            current.started_at = current.scheduled_start
            current.save(update_fields=["started_at"])
        return current

    return qs.filter(scheduled_start__gt=now).order_by("scheduled_start").first()


@transaction.atomic
def advance(behaviour, now=None):
    now = now or timezone.now()

    qs = (
        CharacterActivity.objects.select_for_update()
        .filter(character=behaviour.character)
        .exclude(scheduled_start__isnull=True)
        .exclude(scheduled_end__isnull=True)
        .order_by("scheduled_start")
    )

    current = qs.filter(scheduled_start__lte=now, scheduled_end__gt=now).first()
    if not current:
        return sync_to_now(behaviour, now=now)

    if not current.is_complete:
        if current.started_at is None:
            current.started_at = current.scheduled_start

        duration = max(0, int((now - current.started_at).total_seconds()))
        behaviour.duration = duration
        current.xp_gained = current.calculate_base_xp(duration)
        current.completed_at = now
        current.is_complete = True
        current.save(
            update_fields=[
                "started_at",
                "duration",
                "xp_gained",
                "completed_at",
                "is_complete",
            ]
        )

    nxt = qs.filter(scheduled_start__gte=current.scheduled_end).first()
    if nxt and nxt.started_at is None and nxt.scheduled_start <= now:
        nxt.started_at = nxt.scheduled_start
        nxt.save(update_fields=["started_at"])

    return nxt


def delete_day(behaviour, date):
    day = behaviour.days.filter(date=date).first()
    if not day:
        return
    day.delete_all()
    day.delete()


def get_current_activity(behaviour):
    now = timezone.now()
    activity = (
        CharacterActivity.objects.filter(
            character=behaviour.character,
            started_at__lte=now,
            scheduled_end__gt=now,
            completed_at__isnull=True,
        )
        .order_by("scheduled_start")
        .first()
    )
    if not activity:
        return None

    return activity


def interrupt_current_activity(behaviour, boost_ended=False):
    now = timezone.now()
    activity = get_current_activity(behaviour)
    if not activity or activity.is_complete:
        return None

    new_activity = CharacterActivity.objects.create(
        character=behaviour.character,
        kind=activity.kind,
        name=activity.name,
        scheduled_end=activity.scheduled_end,
    )
    activity.complete_now()

    new_activity.started_at = now
    new_activity.save(update_fields=["started_at"])
    return new_activity
