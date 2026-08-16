import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("economy", "0005_backfill_building_capabilities"),
        ("locations", "0010_building_open_time_override_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="goodsconversionstate",
            name="building",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="conversion_states",
                to="locations.building",
            ),
        ),
        migrations.AddField(
            model_name="goodsconversionstate",
            name="activity",
            field=models.CharField(
                blank=True,
                choices=[
                    ("milling", "Milling"),
                    ("baking", "Baking"),
                    ("farming", "Farming"),
                ],
                max_length=20,
                null=True,
            ),
        ),
    ]
