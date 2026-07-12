# Generated manually to match 0005_task_first_completed_at pattern

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("progression", "0005_task_first_completed_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="due_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="subtasks",
                to="progression.task",
            ),
        ),
    ]
