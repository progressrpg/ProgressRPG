# Hand-written (see PR description): one modifier row per (key, owner).
#
# WILL FAIL if duplicate rows already exist. That is deliberate - a
# duplicate is a symptom worth looking at, not something to delete blindly
# from a data migration. To check before deploying:
#
#     SELECT key, character_id, player_id, COUNT(*)
#     FROM gameplay_xpmodifier
#     GROUP BY key, character_id, player_id
#     HAVING COUNT(*) > 1;
#
# Two constraints rather than one over (scope, key, owner): Postgres treats
# NULLs as distinct in a unique constraint, and both owner FKs are nullable,
# so a single constraint would quietly permit duplicates on whichever side
# was null.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gameplay", "0012_xpmodifier_stacking"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="xpmodifier",
            constraint=models.UniqueConstraint(
                condition=models.Q(("character__isnull", False)),
                fields=("key", "character"),
                name="uniq_xpmodifier_key_per_character",
            ),
        ),
        migrations.AddConstraint(
            model_name="xpmodifier",
            constraint=models.UniqueConstraint(
                condition=models.Q(("player__isnull", False)),
                fields=("key", "player"),
                name="uniq_xpmodifier_key_per_player",
            ),
        ),
    ]
