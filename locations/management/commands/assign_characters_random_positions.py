# assign_characters_random_positions.py

from django.core.management.base import BaseCommand
from django.db import transaction
from locations.models import Position
from character.models import Character
import random


class Command(BaseCommand):
    help = "Assigns all characters a random position (in metres)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--xmin", type=int, default=0, help="Minimum X coordinate (default: 0)"
        )
        parser.add_argument(
            "--xmax",
            type=int,
            default=1000,
            help="Maximum X coordinate (default: 1000)",
        )
        parser.add_argument(
            "--ymin", type=int, default=0, help="Minimum Y coordinate (default: 0)"
        )
        parser.add_argument(
            "--ymax",
            type=int,
            default=1000,
            help="Maximum Y coordinate (default: 1000)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        xmin = options["xmin"]
        xmax = options["xmax"]
        ymin = options["ymin"]
        ymax = options["ymax"]

        characters = Character.objects.all()
        if not characters.exists():
            self.stdout.write(self.style.WARNING("No characters found."))
            return

        self.stdout.write(
            f"Assigning random positions (X{xmin}-{xmax}, Y{ymin}-{ymax}) to {characters.count()} characters...\n"
        )

        for char in characters:
            # Create a position if missing
            if not char.position:
                char.position = Position.objects.create(x=0, y=0)
                char.save(update_fields=["position"])

            new_pos = Position.objects.create(
                x=random.randint(xmin, xmax),
                y=random.randint(ymin, ymax),
            )

            char.move_to(new_pos)

            self.stdout.write(f"{char.name} → ({char.position.x}, {char.position.y})")

        self.stdout.write(
            self.style.SUCCESS("\nAll characters assigned random positions!")
        )
