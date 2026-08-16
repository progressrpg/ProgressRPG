import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("character", "0003_initial"),
        ("progression", "0005_task_first_completed_at"),
    ]

    operations = [
        migrations.CreateModel(
            name="SkillGroup",
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
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("last_updated", models.DateTimeField(auto_now=True)),
                (
                    "role",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="skill_groups",
                        to="progression.role",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="SkillDefinition",
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
                ("min_proficiency", models.PositiveIntegerField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("last_updated", models.DateTimeField(auto_now=True)),
                (
                    "role",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="skill_definitions",
                        to="progression.role",
                    ),
                ),
                (
                    "gate_group",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="gated_skill_definitions",
                        to="progression.skillgroup",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="CharacterRole",
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
                ("assigned_at", models.DateTimeField(auto_now_add=True)),
                (
                    "character",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="character_roles",
                        to="character.character",
                    ),
                ),
                (
                    "role",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="character_roles",
                        to="progression.role",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="characterrole",
            constraint=models.UniqueConstraint(
                fields=("character", "role"), name="unique_character_role"
            ),
        ),
        migrations.AddField(
            model_name="characterskill",
            name="skill_definition",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="character_skills",
                to="progression.skilldefinition",
            ),
        ),
    ]
