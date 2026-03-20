from django.core.management.base import BaseCommand
from django.core.management import call_command
import os


class Command(BaseCommand):
    help = "Runs full project seed: migrate, fixtures, superuser, world, and character tasks"

    def handle(self, *args, **options):
        self.stdout.write("⏳ Running migrations...")
        call_command("migrate")

        self.stdout.write("⏳ Loading fixtures...")
        call_command("loaddata", "seed_data.json")

        self.stdout.write("⏳ Creating superuser...")
        call_command("seed_superuser")

        self.stdout.write("⏳ Setting up world...")
        call_command("setup_world")

        self.stdout.write("⏳ Generating character days...")
        try:
            from character.tasks import generate_character_days

            generate_character_days()
            self.stdout.write("Character days generation complete.")
        except ImportError as e:
            self.stderr.write(f"Could not generate character days: {e}")

        self.stdout.write(self.style.SUCCESS("✅ Full seed workflow finished."))
