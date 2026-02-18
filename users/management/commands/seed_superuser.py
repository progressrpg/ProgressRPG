from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os


class Command(BaseCommand):
    help = "Creates a superuser from environment variables if it doesn't exist"

    def handle(self, *args, **options):
        User = get_user_model()
        email = os.getenv("DJANGO_SUPERUSER_EMAIL", "duncan@progressrpg.com")
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD")

        if password is None:
            self.stderr.write("DJANGO_SUPERUSER_PASSWORD env var not set")
            return

        if User.objects.filter(email=email).exists():
            self.stdout.write(f"Superuser with email '{email}' already exists.")
        else:
            User.objects.create_superuser(email=email, password=password)
            self.stdout.write(f"Superuser with email '{email}' created successfully.")
