from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0002_userlogin_and_player_presence"),
    ]

    operations = [
        migrations.CreateModel(
            name="PlayerCurrency",
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
                    "player",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="currencies",
                        to="users.player",
                    ),
                ),
            ],
            options={
                "unique_together": {("player", "name")},
            },
        ),
    ]
