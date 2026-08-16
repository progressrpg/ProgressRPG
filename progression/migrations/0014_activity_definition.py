import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("progression", "0013_merge_role_skill_taxonomy_activity_catalog"),
    ]

    operations = [
        migrations.CreateModel(
            name="ActivityDefinition",
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
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True, max_length=2000)),
                (
                    "kind",
                    models.CharField(
                        choices=[
                            ("sleep", "Sleeping"),
                            ("morning", "Morning routine"),
                            ("work", "Working"),
                            ("meal", "Meal"),
                            ("leisure", "Leisure"),
                            ("wind_down", "Wind down"),
                            ("rest", "Resting"),
                            ("idle", "Idling"),
                        ],
                        max_length=50,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("last_updated", models.DateTimeField(auto_now=True)),
                (
                    "skill",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="activity_definitions",
                        to="progression.skilldefinition",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="characteractivity",
            name="activity_definition",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="character_activities",
                to="progression.activitydefinition",
            ),
        ),
    ]
