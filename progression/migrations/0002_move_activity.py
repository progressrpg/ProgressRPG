from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("progression", "0001_initial"),
        ("gameplay", "0096_activity_xp_gained"),
    ]

    operations = [
        migrations.AlterModelTable(
            name="activity",
            table="progression_activity",
        ),
    ]
