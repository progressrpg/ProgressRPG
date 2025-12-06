import random
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from math import sqrt
from locations.models import PopulationCentre
from character.models import Character


def distance(p1: Point, p2: Point):
    dx = p1.x - p2.x
    dy = p1.y - p2.y
    return sqrt(dx * dx + dy * dy)


class Command(BaseCommand):
    help = "Randomly distribute all characters to population centres"

    def add_arguments(self, parser):
        parser.add_argument(
            "--radius",
            type=int,
            default=10,
            help="Max distance from the centre to place characters",
        )

    def handle(self, *args, **options):
        radius = options["radius"]

        centres = list(PopulationCentre.objects.all())
        characters = list(Character.objects.all())

        if not centres:
            self.stdout.write(self.style.WARNING("No population centres found"))
            return
        if not characters:
            self.stdout.write(self.style.WARNING("No characters found"))
            return

        for idx, char in enumerate(characters, start=1):
            # Assign a random centre
            centre = random.choice(centres)

            # Random offset within radius
            for attempt in range(50):
                offset_x = random.uniform(-radius, radius)
                offset_y = random.uniform(-radius, radius)
                new_location = Point(
                    centre.location.x + offset_x,
                    centre.location.y + offset_y,
                    srid=centre.location.srid,
                )

                # Optional: avoid overlapping exact locations
                # You could add a check here if desired
                break  # accept first valid placement

            char.location = new_location
            char.save(update_fields=["location"])
            self.stdout.write(f"{char} placed at {new_location} near {centre.name}")

        self.stdout.write(self.style.SUCCESS("All characters distributed"))
