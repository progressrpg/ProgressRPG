"""
One definition of "which day is this?", shared by everything that counts
something per day: daily goals, login streaks, offline-logging caps and the
activity timeline.

A player's day does not start at midnight. It starts at their
``day_start_time`` (default 02:00) in their own timezone, so work done late
on Tuesday evening counts for Tuesday even when the clock has already rolled
over to Wednesday. A day is named for the calendar date it *starts* on: with
a 02:00 cutoff, the span Tue 02:00 -> Wed 02:00 is "Tuesday".

Every function here takes the user explicitly. That is deliberate:
``UserTimezoneMiddleware`` only activates the user's timezone during HTTP
requests, so anything relying on ambient ``timezone.localdate()`` silently
falls back to ``settings.TIME_ZONE`` (UTC) inside Celery tasks and websocket
consumers - which meant the same player got different day boundaries
depending on whether they pressed Submit or the server closed the session
for them.
"""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.utils import timezone

# Used when a user has no usable timezone or cutoff stored. Mirrors the
# model defaults rather than the server's TIME_ZONE, so a missing value
# degrades to the same answer a freshly-created user would get.
DEFAULT_DAY_START = time(2, 0)
DEFAULT_TIMEZONE = ZoneInfo("UTC")


def _user_of(owner):
    """
    Accept either a CustomUser or a Player, since callers naturally hold one
    or the other (daily goals work in players, logins work in users).
    """
    return getattr(owner, "user", owner)


def day_settings(owner) -> tuple[ZoneInfo, time]:
    """Return the (timezone, day start) pair that defines `owner`'s day."""
    user = _user_of(owner)

    raw_timezone = getattr(user, "timezone", None)
    if isinstance(raw_timezone, ZoneInfo):
        tz = raw_timezone
    else:
        try:
            tz = ZoneInfo(str(raw_timezone)) if raw_timezone else DEFAULT_TIMEZONE
        except (ZoneInfoNotFoundError, ValueError):
            tz = DEFAULT_TIMEZONE

    day_start = getattr(user, "day_start_time", None) or DEFAULT_DAY_START
    return tz, day_start


def logical_date_for(owner, moment: datetime) -> date:
    """
    The logical day `moment` falls in for `owner`.

    `moment` must be timezone-aware; a naive datetime has no single answer
    here and would quietly produce a wrong day.
    """
    if timezone.is_naive(moment):
        raise ValueError("logical_date_for() requires an aware datetime")

    tz, day_start = day_settings(owner)
    local = moment.astimezone(tz)

    if local.time() < day_start:
        return local.date() - timedelta(days=1)
    return local.date()


def logical_day_bounds(owner, day: date) -> tuple[datetime, datetime]:
    """
    The half-open [start, end) instants of `owner`'s logical `day`.

    Built from local wall-clock times rather than by shifting a UTC instant,
    so the boundary lands at the configured hour on both sides of a DST
    transition instead of drifting by an hour twice a year. On the rare day
    where the cutoff itself is skipped by a spring-forward, ZoneInfo resolves
    the nonexistent local time to a real instant.
    """
    tz, day_start = day_settings(owner)
    start = datetime.combine(day, day_start, tzinfo=tz)
    end = datetime.combine(day + timedelta(days=1), day_start, tzinfo=tz)
    return start, end


def current_logical_date(owner) -> date:
    """The logical day `owner` is in right now."""
    return logical_date_for(owner, timezone.now())
