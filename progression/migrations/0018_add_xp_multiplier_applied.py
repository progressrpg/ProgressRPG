# Generated manually for symbiotic XP multiplier system

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("progression", "0017_alter_characteractivity_name_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="characteractivity",
            name="xp_multiplier_applied",
            field=models.FloatField(default=1.0),
        ),
    ]
