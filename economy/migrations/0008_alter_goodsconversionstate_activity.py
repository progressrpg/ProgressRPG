from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("economy", "0007_backfill_conversion_state_activity"),
    ]

    operations = [
        migrations.AlterField(
            model_name="goodsconversionstate",
            name="activity",
            field=models.CharField(
                choices=[
                    ("milling", "Milling"),
                    ("baking", "Baking"),
                    ("farming", "Farming"),
                ],
                max_length=20,
            ),
        ),
        migrations.AddConstraint(
            model_name="goodsconversionstate",
            constraint=models.UniqueConstraint(
                fields=("building", "activity"),
                name="uniq_conversion_state_per_activity",
            ),
        ),
    ]
