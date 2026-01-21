# Generated migration to rename profile fields to player

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("progression", "0020_alter_characteractivity_kind"),
        ("users", "0036_rename_profile_to_player"),
    ]

    operations = [
        migrations.RenameField(
            model_name="category",
            old_name="profile",
            new_name="player",
        ),
        migrations.RenameField(
            model_name="playerskill",
            old_name="profile",
            new_name="player",
        ),
        migrations.RenameField(
            model_name="playeractivity",
            old_name="profile",
            new_name="player",
        ),
        migrations.RenameField(
            model_name="project",
            old_name="profile",
            new_name="player",
        ),
        migrations.RenameField(
            model_name="task",
            old_name="profile",
            new_name="player",
        ),
        migrations.AlterField(
            model_name="category",
            name="player",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="categories",
                to="users.player",
            ),
        ),
        migrations.AlterField(
            model_name="playerskill",
            name="player",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="skills",
                to="users.player",
            ),
        ),
        migrations.AlterField(
            model_name="playeractivity",
            name="player",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="activities",
                to="users.player",
            ),
        ),
        migrations.AlterField(
            model_name="project",
            name="player",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="projects",
                to="users.player",
            ),
        ),
        migrations.AlterField(
            model_name="task",
            name="player",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="tasks",
                to="users.player",
            ),
        ),
    ]
