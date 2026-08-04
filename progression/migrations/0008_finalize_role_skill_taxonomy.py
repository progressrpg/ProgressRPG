import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("progression", "0007_migrate_role_skill_data"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="role",
            name="character",
        ),
        migrations.RemoveField(
            model_name="characterskill",
            name="name",
        ),
        migrations.RemoveField(
            model_name="characterskill",
            name="description",
        ),
        migrations.RemoveField(
            model_name="characterskill",
            name="level",
        ),
        migrations.RemoveField(
            model_name="characterskill",
            name="roles",
        ),
        migrations.AlterField(
            model_name="characterskill",
            name="skill_definition",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="character_skills",
                to="progression.skilldefinition",
            ),
        ),
        migrations.AddConstraint(
            model_name="characterskill",
            constraint=models.UniqueConstraint(
                fields=("character", "skill_definition"),
                name="unique_character_skill_definition",
            ),
        ),
    ]
