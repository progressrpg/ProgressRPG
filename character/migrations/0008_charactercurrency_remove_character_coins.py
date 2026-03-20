from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("character", "0007_character_building_character_current_node_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="CharacterCurrency",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=50)),
                ("earned", models.PositiveIntegerField(default=0)),
                ("spent", models.PositiveIntegerField(default=0)),
                ("last_calculated_at", models.DateTimeField(blank=True, null=True)),
                (
                    "character",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="currencies",
                        to="character.character",
                    ),
                ),
            ],
            options={
                "unique_together": {("character", "name")},
            },
        ),
        migrations.RemoveField(
            model_name="character",
            name="coins",
        ),
    ]
