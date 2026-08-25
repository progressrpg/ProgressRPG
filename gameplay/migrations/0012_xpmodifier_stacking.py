# Hand-written (see PR description): adds XpModifier.stacking.
#
# Behaviourally inert. Every existing row takes the "multiplicative"
# default, which is how every modifier already combined, so the live boost
# is unchanged by applying this.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gameplay", "0011_disable_renamed_autocomplete_beat_task"),
    ]

    operations = [
        migrations.AddField(
            model_name="xpmodifier",
            name="stacking",
            field=models.CharField(
                choices=[
                    ("additive", "Additive"),
                    ("multiplicative", "Multiplicative"),
                ],
                default="multiplicative",
                help_text=(
                    "Additive modifiers sum with each other before multiplying "
                    "with the multiplicative ones. Defaults to multiplicative, "
                    "which is how every modifier behaved before this field "
                    "existed."
                ),
                max_length=16,
            ),
        ),
    ]
