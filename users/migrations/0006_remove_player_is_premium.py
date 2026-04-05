from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0005_customuser_timezone"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="player",
            name="is_premium",
        ),
    ]
