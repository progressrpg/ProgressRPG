# Generated manually for symbiotic XP multiplier system

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("character", "0015_remove_playercharacterlink_one_active_link_per_profile_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="playercharacterlink",
            name="player_came_online_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text="When the player came online while linked to this character",
            ),
        ),
    ]
