import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gameplay", "0007_clear_questtimer_quest"),
    ]

    operations = [
        migrations.AlterField(
            model_name="questtimer",
            name="quest",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="quest_timer",
                to="gameplay.quest",
            ),
        ),
    ]
