# Generated migration to rename profile fields to player

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("character", "0013_remove_character_is_npc"),
        ("users", "0036_rename_profile_to_player"),
    ]

    operations = [
        migrations.RenameField(
            model_name="playercharacterlink",
            old_name="profile",
            new_name="player",
        ),
        migrations.AlterField(
            model_name="playercharacterlink",
            name="player",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="character_link",
                to="users.player",
            ),
        ),
    ]
