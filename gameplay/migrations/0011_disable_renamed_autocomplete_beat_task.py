from django.db import migrations

# Renamed when the auto-complete paths became auto-pause paths.
OLD_NAME = "auto_complete_timers_for_stale_players"


def disable_old_entry(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(name=OLD_NAME).update(enabled=False)


def reenable_old_entry(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(name=OLD_NAME).update(enabled=True)


class Migration(migrations.Migration):
    """
    django_celery_beat's DatabaseScheduler only ADDS entries from
    app.conf.beat_schedule - it never removes ones no longer listed (see
    locations/migrations/0002 for the same problem). Renaming this beat
    entry would otherwise leave the old row enabled and pointing at a task
    that no longer exists, which fails quietly in the worker log while
    looking, from the schedule, like the sweep is still running.
    """

    dependencies = [
        ("gameplay", "0010_activitytimer_limit_reason_and_more"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(disable_old_entry, reenable_old_entry),
    ]
