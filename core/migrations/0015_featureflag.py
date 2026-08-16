from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0014_gamesettings_activity_compaction_cutoff_days"),
        ("server_management", "0005_delete_featureflag"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="FeatureFlag",
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
                        ("key", models.CharField(max_length=100, unique=True)),
                        (
                            "access_groups",
                            models.JSONField(
                                default=list,
                                help_text="List of groups that can access this feature: 'all', 'premium', 'testers'.",
                            ),
                        ),
                        ("description", models.TextField(blank=True)),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        ("updated_at", models.DateTimeField(auto_now=True)),
                    ],
                    options={
                        "ordering": ("key",),
                    },
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql="ALTER TABLE server_management_featureflag RENAME TO core_featureflag",
                    reverse_sql="ALTER TABLE core_featureflag RENAME TO server_management_featureflag",
                ),
            ],
        ),
    ]
