"""
Backfill `PlayerActivity.logical_date` for sessions recorded before the
column existed.

Derived from `started_at` where it is set, falling back to `completed_at`
for older rows that predate start-time tracking. Some historical rows will
therefore land on a different day than the UI previously showed for them -
that is the point of the change, not a defect, but it is a one-off
rewrite of how past days are grouped.

The day rule is reimplemented here rather than imported from
`progression.day_boundaries`: migrations must keep working even after that
module changes.
"""

from datetime import time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.db import migrations
from django.db.models import Q

BATCH_SIZE = 2000
DEFAULT_DAY_START = time(2, 0)
UTC = ZoneInfo("UTC")


def _day_settings(user):
    raw = getattr(user, "timezone", None)
    if isinstance(raw, ZoneInfo):
        tz = raw
    else:
        try:
            tz = ZoneInfo(str(raw)) if raw else UTC
        except (ZoneInfoNotFoundError, ValueError):
            tz = UTC
    return tz, getattr(user, "day_start_time", None) or DEFAULT_DAY_START


def _logical_date(user, moment):
    tz, day_start = _day_settings(user)
    local = moment.astimezone(tz)
    if local.time() < day_start:
        return local.date() - timedelta(days=1)
    return local.date()


def backfill(apps, schema_editor):
    PlayerActivity = apps.get_model("progression", "PlayerActivity")

    batch = []
    queryset = (
        PlayerActivity.objects.filter(logical_date__isnull=True)
        .filter(Q(started_at__isnull=False) | Q(completed_at__isnull=False))
        .select_related("player__user")
        .iterator(chunk_size=BATCH_SIZE)
    )
    for activity in queryset:
        moment = activity.started_at or activity.completed_at
        activity.logical_date = _logical_date(activity.player.user, moment)
        batch.append(activity)
        if len(batch) >= BATCH_SIZE:
            PlayerActivity.objects.bulk_update(batch, ["logical_date"])
            batch = []

    if batch:
        PlayerActivity.objects.bulk_update(batch, ["logical_date"])


def unbackfill(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("progression", "0024_playeractivity_logical_date_and_more"),
        # The rule reads `day_start_time`, so that column has to exist first.
        ("users", "0014_customuser_day_start_time_userlogin_logical_date"),
    ]

    operations = [
        migrations.RunPython(backfill, unbackfill),
    ]
