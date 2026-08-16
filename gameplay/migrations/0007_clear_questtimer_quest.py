from django.db import migrations


def clear_quest(apps, schema_editor):
    QuestTimer = apps.get_model("gameplay", "QuestTimer")
    # `quest` is about to be retargeted from progression.CharacterQuest to
    # gameplay.Quest - the old values are ids into a table that's going
    # away, so clear them rather than let them dangle/misresolve.
    QuestTimer.objects.exclude(quest__isnull=True).update(quest=None)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("gameplay", "0006_currency"),
    ]

    operations = [
        migrations.RunPython(clear_quest, noop_reverse),
    ]
