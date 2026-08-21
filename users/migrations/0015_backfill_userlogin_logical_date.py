"""
Backfill `UserLogin.logical_date` for logins recorded before the column
existed, so streaks computed from stored logical dates don't see a gap.

The day rule is reimplemented here rather than imported from
`progression.day_boundaries`: migrations must keep working even after that
module changes, and historical models can't call model methods anyway.
"""

from datetime import time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.db import migrations

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
    UserLogin = apps.get_model("users", "UserLogin")

    batch = []
    queryset = (
        UserLogin.objects.filter(logical_date__isnull=True, timestamp__isnull=False)
        .select_related("user")
        .iterator(chunk_size=BATCH_SIZE)
    )
    for login in queryset:
        login.logical_date = _logical_date(login.user, login.timestamp)
        batch.append(login)
        if len(batch) >= BATCH_SIZE:
            UserLogin.objects.bulk_update(batch, ["logical_date"])
            batch = []

    if batch:
        UserLogin.objects.bulk_update(batch, ["logical_date"])


def unbackfill(apps, schema_editor):
    # Nothing to undo: the column goes with the schema migration, and
    # clearing it would only lose information if this were re-applied.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0014_customuser_day_start_time_userlogin_logical_date"),
    ]

    operations = [
        migrations.RunPython(backfill, unbackfill),
    ]
