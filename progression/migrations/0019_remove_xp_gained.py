from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("progression", "0018_migrate_xp_gained_to_reward_breakdown"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="characteractivity",
            name="xp_gained",
        ),
        migrations.RemoveField(
            model_name="playeractivity",
            name="xp_gained",
        ),
    ]
