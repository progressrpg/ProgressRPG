# Generated migration

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("character", "0015_remove_playercharacterlink_one_active_link_per_profile_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="playercharacterlink",
            name="player_active_since",
            field=models.DateTimeField(
                blank=True,
                help_text="When the player started an activity with this character",
                null=True,
            ),
        ),
    ]
