from datetime import timedelta, datetime, time
from django.utils import timezone
import logging
from progression.models import CharacterActivity

logger = logging.getLogger("django")


def window_for_date(date, behaviour):
    # reuse Behaviour logic (returns dawn, dusk, next_dawn); use it to get the sleep tail
    dawn, dusk, next_dawn = behaviour._day_window(date)
    tz = timezone.get_current_timezone()
    window_start = timezone.make_aware(datetime.combine(date, time(0, 0)), tz)
    # include sleep tail so checks match generate_day's delete logic
    # sleep_end is the tail returned via next_dawn for the following day; generate_day uses its computed sleep_end
    # fallback to end-of-day if you don't want the tail
    window_end = (
        next_dawn  # or timezone.make_aware(datetime.combine(date, time(23,59,59)), tz)
    )
    return window_start, window_end


def activities_exist_for_date(character, date):
    window_start, window_end = window_for_date(date, character.behaviour)
    return CharacterActivity.objects.filter(
        character=character,
        scheduled_start__lt=window_end,
        scheduled_end__gt=window_start,
    ).exists()


def ensure_day_activities(character, date, create_if_missing=True):
    if not activities_exist_for_date(character, date) and create_if_missing:
        # generate_day is atomic and does cleanup/select_for_update internally
        return character.behaviour.generate_day(date)
    return None
