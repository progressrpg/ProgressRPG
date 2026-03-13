from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_login_history(apps, schema_editor):
    Player = apps.get_model("users", "Player")
    UserLogin = apps.get_model("users", "UserLogin")

    for player in Player.objects.select_related("user"):
        candidate_timestamp = player.last_login or player.user.last_login

        if (
            candidate_timestamp
            and not UserLogin.objects.filter(user=player.user).exists()
        ):
            login = UserLogin.objects.create(user=player.user)
            UserLogin.objects.filter(pk=login.pk).update(timestamp=candidate_timestamp)

        if candidate_timestamp and player.last_seen is None:
            player.last_seen = candidate_timestamp
            player.save(update_fields=["last_seen"])


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserLogin",
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
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="logins",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="player",
            name="active_connections",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="player",
            name="last_seen",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(backfill_login_history, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="player",
            name="last_login",
        ),
        migrations.RemoveField(
            model_name="player",
            name="login_streak",
        ),
        migrations.RemoveField(
            model_name="player",
            name="login_streak_max",
        ),
        migrations.RemoveField(
            model_name="player",
            name="total_logins",
        ),
    ]
