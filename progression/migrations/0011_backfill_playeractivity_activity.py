from django.db import migrations


def backfill_activity(apps, schema_editor):
    PlayerActivity = apps.get_model("progression", "PlayerActivity")
    Activity = apps.get_model("progression", "Activity")

    activity_cache = {}  # (player_id, normalized_name.casefold()) -> Activity.id

    for session in (
        PlayerActivity.objects.filter(activity__isnull=True)
        .exclude(name="")
        .order_by("id")
    ):
        normalized_name = session.name.strip()
        if not normalized_name:
            continue

        cache_key = (session.player_id, normalized_name.casefold())
        activity_id = activity_cache.get(cache_key)
        if activity_id is None:
            activity = Activity.objects.filter(
                player_id=session.player_id, name__iexact=normalized_name
            ).first()
            if activity is None:
                activity = Activity.objects.create(
                    player_id=session.player_id, name=normalized_name
                )
            activity_id = activity.id
            activity_cache[cache_key] = activity_id

        session.activity_id = activity_id
        session.save(update_fields=["activity"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("progression", "0010_activity_catalog"),
    ]

    operations = [
        migrations.RunPython(backfill_activity, noop_reverse),
    ]
