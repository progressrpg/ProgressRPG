from django.db import migrations

SQL = """
UPDATE gameplay_activitytimer t
SET activity_id = NULL
WHERE activity_id IS NOT NULL
AND NOT EXISTS (
  SELECT 1 FROM progression_activity a WHERE a.id = t.activity_id
);
"""


class Migration(migrations.Migration):
    dependencies = [
        ("gameplay", "0098_alter_activitytimer_activity_delete_activity"),
        ("progression", "0002_move_activity"),
    ]

    operations = [
        migrations.RunSQL(SQL, migrations.RunSQL.noop),
    ]
