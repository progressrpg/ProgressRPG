from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("progression", "0011_backfill_playeractivity_activity"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="playeractivity",
            name="group_key",
        ),
    ]
