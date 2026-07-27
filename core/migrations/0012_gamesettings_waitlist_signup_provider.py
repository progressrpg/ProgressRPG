from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0011_merge_20260709_2330"),
    ]

    operations = [
        migrations.AddField(
            model_name="gamesettings",
            name="waitlist_signup_provider",
            field=models.CharField(
                choices=[("mailchimp", "Mailchimp"), ("internal", "Internal")],
                default="mailchimp",
                max_length=20,
            ),
        ),
    ]
