from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("progression", "0016_finalize_activity_definition"),
    ]

    operations = [
        migrations.AddField(
            model_name="characteractivity",
            name="reward_breakdown",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="playeractivity",
            name="reward_breakdown",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
