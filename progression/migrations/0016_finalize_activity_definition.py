import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("progression", "0015_migrate_activity_data"),
        ("gameplay", "0008_alter_questtimer_quest"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="characteractivity",
            name="description",
        ),
        migrations.RemoveField(
            model_name="characteractivity",
            name="kind",
        ),
        migrations.RemoveField(
            model_name="characteractivity",
            name="name",
        ),
        migrations.AlterField(
            model_name="characteractivity",
            name="activity_definition",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="character_activities",
                to="progression.activitydefinition",
            ),
        ),
        migrations.DeleteModel(
            name="CharacterQuest",
        ),
    ]
