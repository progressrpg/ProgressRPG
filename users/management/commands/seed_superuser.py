from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
import os


class Command(BaseCommand):
    help = "Creates a superuser from environment variables if it doesn't exist"

    def handle(self, *args, **options):
        User = get_user_model()
        email = os.getenv("DJANGO_SUPERUSER_EMAIL", "gaidheal01@gmail.com")
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD")

        if password is None:
            self.stderr.write("DJANGO_SUPERUSER_PASSWORD env var not set")
            return

        user = User.objects.filter(email=email).first()
        if user is not None:
            self.stdout.write(f"Superuser with email '{email}' already exists.")
        else:
            user = User.objects.create_superuser(email=email, password=password)
            self.stdout.write(f"Superuser with email '{email}' created successfully.")

        # Grants access to every FeatureFlag gated on the "testers" access
        # group (see core.models.FeatureFlag) — the dev/seed superuser
        # should see everything behind a tester flag by default.
        testers_group, _created = Group.objects.get_or_create(name="Testers")
        user.groups.add(testers_group)
