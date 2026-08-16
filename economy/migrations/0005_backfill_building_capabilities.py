from django.db import migrations

# Maps every existing building_type with a production meaning today onto
# the new capability it should get, per
# .claude/plans/building-capabilities-plan.md. Types not listed
# (residential, hall, market, communal, inn, granary) get no capability -
# granary is storage, not a labor-capped production activity (see
# BuildingCapability's docstring), and the rest have no production role at
# all today.
BUILDING_TYPE_TO_ACTIVITY = {
    "mill": "milling",
    "bakery": "baking",
    "field_shelter": "farming",
}


def backfill_capabilities(apps, schema_editor):
    Building = apps.get_model("locations", "Building")
    BuildingCapability = apps.get_model("economy", "BuildingCapability")

    capabilities = [
        BuildingCapability(building=building, activity=activity)
        for building_type, activity in BUILDING_TYPE_TO_ACTIVITY.items()
        for building in Building.objects.filter(building_type=building_type)
    ]
    BuildingCapability.objects.bulk_create(capabilities)


def remove_backfilled_capabilities(apps, schema_editor):
    BuildingCapability = apps.get_model("economy", "BuildingCapability")
    BuildingCapability.objects.filter(
        activity__in=BUILDING_TYPE_TO_ACTIVITY.values()
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("economy", "0004_buildingcapability"),
    ]

    operations = [
        migrations.RunPython(backfill_capabilities, remove_backfilled_capabilities),
    ]
