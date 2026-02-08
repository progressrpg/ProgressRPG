from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("character", "0008_character_building_character_current_node_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="playercharacterlink",
            old_name="date_linked",
            new_name="linked_at",
        ),
        migrations.RenameField(
            model_name="playercharacterlink",
            old_name="date_unlinked",
            new_name="unlinked_at",
        ),
    ]
