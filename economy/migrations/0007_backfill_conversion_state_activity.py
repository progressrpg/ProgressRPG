from django.db import migrations

# Every existing GoodsConversionState row was created by
# advance_mill_economy_tick or advance_bakery_economy_tick (see
# economy/tasks.py), so its activity is fully determined by its
# building's building_type at the time this migration runs.
BUILDING_TYPE_TO_ACTIVITY = {
    "mill": "milling",
    "bakery": "baking",
}


def backfill_activity(apps, schema_editor):
    GoodsConversionState = apps.get_model("economy", "GoodsConversionState")

    for state in GoodsConversionState.objects.select_related("building"):
        activity = BUILDING_TYPE_TO_ACTIVITY.get(state.building.building_type)
        if activity is None:
            # No known production activity for this building - the state
            # row is meaningless without one, and none should exist today.
            state.delete()
            continue
        state.activity = activity
        state.save(update_fields=["activity"])


def noop_reverse(apps, schema_editor):
    # Reversing 0006/0008 already drops the activity column/constraint;
    # nothing extra to undo here.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("economy", "0006_goodsconversionstate_activity"),
    ]

    operations = [
        migrations.RunPython(backfill_activity, noop_reverse),
    ]
