from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gameplay", "0005_remove_xpmodifier_link_alter_xpmodifier_scope"),
    ]

    operations = [
        migrations.CreateModel(
            name="Currency",
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
                ("code", models.SlugField(max_length=50, unique=True)),
                ("name", models.CharField(max_length=100)),
                ("symbol", models.CharField(blank=True, max_length=10)),
                ("precision", models.PositiveSmallIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ["code"]},
        ),
    ]
