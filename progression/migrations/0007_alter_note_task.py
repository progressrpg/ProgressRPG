import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("progression", "0006_note"),
    ]

    operations = [
        migrations.AlterField(
            model_name="note",
            name="task",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="note",
                to="progression.task",
            ),
        ),
    ]
