# Generated migration to rename profile to player in EventContribution

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0001_initial"),
        ("users", "0036_rename_profile_to_player"),
    ]

    operations = [
        migrations.RenameField(
            model_name="eventcontribution",
            old_name="profile",
            new_name="player",
        ),
        migrations.AlterField(
            model_name="eventcontribution",
            name="player",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="contribution",
                to="users.player",
            ),
        ),
    ]
