from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("character", "0018_remove_character_last_name_remove_character_name"),
    ]

    operations = [
        migrations.RenameField(
            model_name="character",
            old_name="first_name",
            new_name="given_name",
        ),
    ]
