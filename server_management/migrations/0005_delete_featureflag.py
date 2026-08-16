from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("server_management", "0004_merge_20260630_1318"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(
                    name="FeatureFlag",
                ),
            ],
            database_operations=[],
        ),
    ]
