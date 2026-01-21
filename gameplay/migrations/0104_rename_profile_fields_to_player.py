# Generated migration to rename profile fields to player

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gameplay", "0103_rename_stagesfixed_quest_stages_fixed"),
        ("users", "0036_rename_profile_to_player"),
    ]

    operations = [
        migrations.RenameField(
            model_name="activitytimer",
            old_name="profile",
            new_name="player",
        ),
        migrations.AlterField(
            model_name="activitytimer",
            name="player",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="activity_timer",
                to="users.player",
            ),
        ),
    ]
