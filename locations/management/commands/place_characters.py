from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
import random
import math

from character.models import Character
from locations.models import Building


class Command(BaseCommand):
    help = "Assign existing characters to random buildings and move them there"

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        characters = Character.objects.all()
        if not characters.exists():
            self.stdout.write(self.style.WARNING("No characters found"))
            return

        buildings = Building.objects.filter(building_type="residential")
        if not buildings.exists():
            self.stdout.write(self.style.WARNING("No buildings found"))
            return

        for char in characters:
            building = random.choice(buildings)
            if not building.nodes.exists():
                self.stdout.write(
                    self.style.WARNING(
                        f"Building {building.id} has no nodes – skipping character placement"
                    )
                )
                continue

            if char.is_moving:
                char.journeys.filter(status="active").cancel()

            char.assign_home(building)

            node = None
            rooms = list(char.building.interiorspaces.all())

            if rooms:
                room = random.choice(rooms)
                node = room.nodes.first()
            if not node:
                node = building.nodes.filter(kind=Building.Node.Kind.BUILDING).first()

            char.move_to(node)

            self.stdout.write(
                f"{char.full_name} moved to building {building.name} (ID {building.id})"
            )

        self.stdout.write(self.style.SUCCESS("Characters have been placed"))
