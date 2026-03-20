from django.db import migrations, models
import django.db.models.deletion


def _normalize_code(raw):
    value = (raw or "currency").strip().lower().replace(" ", "_").replace("-", "_")
    value = "".join(ch for ch in value if ch.isalnum() or ch == "_")
    return value or "currency"


def forwards(apps, schema_editor):
    Currency = apps.get_model("gameplay", "Currency")
    PlayerCurrency = apps.get_model("users", "PlayerCurrency")

    for row in PlayerCurrency.objects.all().iterator():
        code = _normalize_code(getattr(row, "name", "currency"))
        currency, _ = Currency.objects.get_or_create(
            code=code,
            defaults={"name": code.replace("_", " ").title()},
        )
        row.currency_id = currency.id
        row.save(update_fields=["currency"])

    # Merge duplicates that may collide after normalization.
    for row in PlayerCurrency.objects.order_by("id"):
        dupes = PlayerCurrency.objects.filter(
            player_id=row.player_id,
            currency_id=row.currency_id,
        ).exclude(id=row.id)
        for dupe in dupes:
            row.earned += dupe.earned
            row.spent += dupe.spent
            if not row.last_calculated_at or (
                dupe.last_calculated_at
                and dupe.last_calculated_at > row.last_calculated_at
            ):
                row.last_calculated_at = dupe.last_calculated_at
            dupe.delete()
        row.save(update_fields=["earned", "spent", "last_calculated_at"])


class Migration(migrations.Migration):

    dependencies = [
        ("gameplay", "0006_currency"),
        ("users", "0003_playercurrency"),
    ]

    operations = [
        migrations.AddField(
            model_name="playercurrency",
            name="currency",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="player_accounts",
                to="gameplay.currency",
            ),
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="playercurrency",
            name="currency",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="player_accounts",
                to="gameplay.currency",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="playercurrency",
            unique_together={("player", "currency")},
        ),
        migrations.RemoveField(
            model_name="playercurrency",
            name="name",
        ),
    ]
