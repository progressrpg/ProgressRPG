from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
import random
import math

from character.models import Character
from locations.models import Building


class Command(BaseCommand):
    help = "Randomly distribute characters around their home building"

    def add_arguments(self, parser):
        parser.add_argument(
            "--radius",
            type=int,
            default=20,
            help="Max distance from the home to place characters",
        )
        parser.add_argument(
            "--assign",
            action="store_true",
            help="Also assign buildings to characters without",
        )

    def handle(self, *args, **options):
        code = 0
        radius = options["radius"]

        if options["assign"]:
            characters = Character.objects.select_related("building")
        else:
            characters = Character.objects.select_related("building").filter(
                building__isnull=False
            )

        if not characters.exists():
            self.stdout.write(self.style.WARNING("No characters found"))
            return

        for char in characters:

            if options["assign"]:
                if not char.building:
                    char.building = random.choice(Building.objects.all())
                    self.stdout.write(
                        f"No building for character {char.id}: now in {char.building.name}"
                    )
                    char.save(update_fields=["building"])

            if not char.building.location:
                self.stdout.write(
                    self.style.WARNING(
                        f"Building {home.id} has no location – skipping character placement"
                    )
                )
                continue

            home = char.building
            # Random offset within radius
            angle = random.random() * 2 * math.pi
            r = random.random() * radius
            offset_x = math.cos(angle) * r
            offset_y = math.sin(angle) * r

            new_location = Point(
                home.location.x + offset_x,
                home.location.y + offset_y,
            )

            char.location = new_location
            self.stdout.write(
                f"{char.full_name} placed at {new_location} near home at {home.location}"
            )

        Character.objects.bulk_update(characters, ["location"])
        self.stdout.write(self.style.SUCCESS("Characters have been placed"))
