# Hand-written (no Django environment available in this session - see the
# plan's Risks section, and the same caveat on the earlier hand-written
# migrations in #829/#833). Adds choices= to Journey.status.
#
# Metadata-only: the column stays CharField(max_length=20), both real
# values ("active"/"complete") and the default are unchanged, so this
# changes no stored data - Django just tracks choices= in migration state,
# so an unmade migration would otherwise show up in
# `manage.py makemigrations --check`.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("locations", "0011_alter_subzone_usage"),
    ]

    operations = [
        migrations.AlterField(
            model_name="journey",
            name="status",
            field=models.CharField(
                choices=[
                    ("active", "Active"),
                    ("complete", "Complete"),
                ],
                default="active",
                max_length=20,
            ),
        ),
    ]
