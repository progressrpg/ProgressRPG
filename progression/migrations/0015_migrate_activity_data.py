from django.db import migrations

# The fixed (non-work) daily blocks each get exactly one canonical,
# skill-less ActivityDefinition - see
# character.services.behaviour_services._fixed_activity_definitions.
FIXED_ACTIVITY_DEFINITIONS = [
    ("sleep", "Sleeping"),
    ("morning", "Waking up"),
    ("meal", "Eating a meal"),
    ("leisure", "Relaxing"),
    ("wind_down", "Winding down"),
]

# General/default work pool (skill-less, so available to any character
# regardless of role) - carried over from the old
# WORK_ACTIVITIES_BY_BUILDING_TYPE["default"] flavor list, which building
# type/role-specific filtering has superseded.
DEFAULT_WORK_ACTIVITIES = [
    "feeding the chickens",
    "collecting eggs",
    "chopping firewood",
    "stacking firewood",
    "hauling water from the well",
    "mending tools",
    "sweeping the yard",
    "mending clothes",
    "clearing debris",
    "delivering goods to neighbours",
]


def migrate_activity_data(apps, schema_editor):
    ActivityDefinition = apps.get_model("progression", "ActivityDefinition")
    CharacterActivity = apps.get_model("progression", "CharacterActivity")

    for kind, name in FIXED_ACTIVITY_DEFINITIONS:
        ActivityDefinition.objects.get_or_create(
            kind=kind, name=name, skill=None, defaults={"description": ""}
        )

    for name in DEFAULT_WORK_ACTIVITIES:
        ActivityDefinition.objects.get_or_create(
            kind="work", name=name, skill=None, defaults={"description": ""}
        )

    # Backfill existing CharacterActivity rows onto a matching (kind, name)
    # ActivityDefinition, deduping identical pairs into one shared row.
    definition_by_kind_and_name = {}
    for activity in CharacterActivity.objects.filter(
        activity_definition__isnull=True
    ).order_by("id"):
        key = (activity.kind, activity.name)
        definition = definition_by_kind_and_name.get(key)
        if definition is None:
            definition, _ = ActivityDefinition.objects.get_or_create(
                kind=activity.kind,
                name=activity.name or "Unnamed activity",
                skill=None,
                defaults={"description": activity.description or ""},
            )
            definition_by_kind_and_name[key] = definition
        activity.activity_definition_id = definition.id
        activity.save(update_fields=["activity_definition"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("progression", "0014_activity_definition"),
    ]

    operations = [
        migrations.RunPython(migrate_activity_data, noop_reverse),
    ]
