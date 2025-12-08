from django.core.management.base import BaseCommand
from gameworld.utils import send_characters_inside


class Command(BaseCommand):
    help = "Test sending all characters inside at night"

    def handle(self, *args, **options):
        chars_moved = send_characters_inside()
        self.stdout.write(
            self.style.SUCCESS(f"{len(chars_moved)} characters sent inside")
        )
        for char in chars_moved:
            self.stdout.write(f"- {char}")
