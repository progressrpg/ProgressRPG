from django.db import migrations


def migrate_xp_gained(apps, schema_editor):
    # Historical rows only ever had the single frozen total, not the full
    # multiplier breakdown that produced it - preserve what we have rather
    # than discard it outright.
    for model_name in ("CharacterActivity", "PlayerActivity"):
        Model = apps.get_model("progression", model_name)
        for activity in Model.objects.filter(xp_gained__isnull=False).only(
            "id", "xp_gained"
        ):
            activity.reward_breakdown = {"xp_gained": activity.xp_gained}
            activity.save(update_fields=["reward_breakdown"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("progression", "0017_add_reward_breakdown"),
    ]

    operations = [
        migrations.RunPython(migrate_xp_gained, noop_reverse),
    ]
