from django.db import migrations

# Placeholder copy - real content is a tracked follow-up (issue #549), not a
# blocker for shipping the unlock mechanism itself. Editable afterward via
# TutorialStepAdmin with no further migration required.
STEPS = [
    {
        "order": 5,
        "unlock_key": "infobar",
        "title": "Your Infobar is unlocked!",
        "body": "Nice work logging your first activity. Check the Infobar "
        "for a quick summary of your progress.",
    },
    {
        "order": 6,
        "unlock_key": "library",
        "title": "The Library is unlocked!",
        "body": "You've logged two activities - the Library is now open, "
        "with your Activities and Tasks all in one place.",
    },
    {
        "order": 7,
        "unlock_key": "map",
        "title": "The Map is unlocked!",
        "body": "You've reached level 4! Explore the Map to see your "
        "character's world.",
    },
]


def seed_steps(apps, schema_editor):
    TutorialStep = apps.get_model("users", "TutorialStep")
    for step in STEPS:
        TutorialStep.objects.get_or_create(
            unlock_key=step["unlock_key"],
            defaults={
                "order": step["order"],
                "title": step["title"],
                "body": step["body"],
            },
        )


def remove_steps(apps, schema_editor):
    TutorialStep = apps.get_model("users", "TutorialStep")
    TutorialStep.objects.filter(
        unlock_key__in=[step["unlock_key"] for step in STEPS]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0016_tutorialstep_unlock_key"),
    ]

    operations = [
        migrations.RunPython(seed_steps, remove_steps),
    ]
