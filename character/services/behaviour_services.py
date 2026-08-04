from __future__ import annotations

import random
from datetime import datetime, time, timedelta

from django.db import transaction
from django.utils import timezone

from character.utils import window_for_date, work_activities_for
from progression.models import ActivityDefinition, CharacterActivity

_FIXED_KINDS = [
    ActivityDefinition.Kind.SLEEP,
    ActivityDefinition.Kind.MORNING,
    ActivityDefinition.Kind.MEAL,
    ActivityDefinition.Kind.LEISURE,
    ActivityDefinition.Kind.WIND_DOWN,
]


def _fixed_activity_definitions():
    """
    The single canonical, skill-less ActivityDefinition for each of the
    day's fixed (non-work) blocks.
    """
    definitions = ActivityDefinition.objects.filter(
        kind__in=_FIXED_KINDS, skill__isnull=True
    )
    return {definition.kind: definition for definition in definitions}


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

    fixed = _fixed_activity_definitions()
    work_activities = rng.sample(work_activities_for(behaviour.character), 2)
    blocks = [
        (fixed[ActivityDefinition.Kind.SLEEP], aware(date, time(0, 0)), morning_start),
        (fixed[ActivityDefinition.Kind.MORNING], morning_start, morning_end),
        (work_activities[0], work1_start, work1_end),
        (fixed[ActivityDefinition.Kind.MEAL], lunch_start, lunch_end),
        (work_activities[1], work2_start, work2_end),
        (fixed[ActivityDefinition.Kind.MEAL], dinner_start, dinner_end),
        (fixed[ActivityDefinition.Kind.LEISURE], leisure_start, leisure_end),
        (fixed[ActivityDefinition.Kind.WIND_DOWN], wind_start, wind_end),
        (fixed[ActivityDefinition.Kind.SLEEP], sleep_start, sleep_end),
    ]

    cleaned = []
    last_end = None
    for activity_definition, start, end in blocks:
        if end <= start:
            continue
        if last_end and start < last_end:
            start = last_end
            if end <= start:
                continue
        cleaned.append((activity_definition, start, end))
        last_end = end

    qs = CharacterActivity.objects.select_for_update().filter(
        character=behaviour.character
    )

    today = timezone.now().date()
    is_past = date < today

    if replace_future:
        window_start = aware(date, time(0, 0))
        window_end = aware(date, time(23, 59, 59))
        to_delete = qs.filter(
            scheduled_start__lt=sleep_end,
            scheduled_end__gt=window_start,
        )
        if not is_past:
            # Only protects activities the character has actually lived
            # through in real time (marked complete by sync_to_now as the
            # day progresses) - a past-date backfill sets is_complete=True
            # on every row purely because the date is past, so that
            # protection would otherwise make regenerating the same past
            # date non-idempotent (duplicated activities instead of
            # replaced ones).
            to_delete = to_delete.filter(is_complete=False)
        to_delete.delete()

    created = []

    for activity_definition, start, end in cleaned:
        activity_kwargs = {
            "character": behaviour.character,
            "activity_definition": activity_definition,
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
        # Same "complete right now, from wherever started_at is" semantics
        # as complete_now() - force-advancing early is just an early
        # completion, so reuse it rather than duplicating the AP/XP logic.
        current.complete_now()

    nxt = qs.filter(scheduled_start__gte=current.scheduled_end).first()
    if nxt and nxt.started_at is None and nxt.scheduled_start <= now:
        nxt.started_at = nxt.scheduled_start
        nxt.save(update_fields=["started_at"])

    return nxt


def delete_day(behaviour, date):
    """
    Delete the character's scheduled CharacterActivity rows covering the
    given date, using the same date-window definition as
    character.utils.activities_exist_for_date.
    """
    window_start, window_end = window_for_date(date, behaviour)

    CharacterActivity.objects.filter(
        character=behaviour.character,
        scheduled_start__lt=window_end,
        scheduled_end__gt=window_start,
    ).delete()


def get_current_activity(behaviour):
    now = timezone.now()
    activity = (
        CharacterActivity.objects.filter(
            character=behaviour.character,
            scheduled_start__lte=now,
            scheduled_end__gt=now,
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
        activity_definition=activity.activity_definition,
        scheduled_end=activity.scheduled_end,
    )
    activity.complete_now()

    new_activity.started_at = now
    new_activity.save(update_fields=["started_at"])
    return new_activity
