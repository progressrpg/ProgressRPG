import random

from django.core.management.base import BaseCommand

from character.models import Character
from locations.models import Building

WORK_BUILDING_TYPES = [
    "granary",
    "inn",
    "mill",
    "bakery",
    "hall",
    "market",
    "communal",
    "field_shelter",
]
MIN_WORKING_AGE = 16
MAX_WORKING_AGE = 65
MIN_WORKERS_PER_BUILDING = 2
MAX_WORKERS_PER_BUILDING = 3


class Command(BaseCommand):
    help = (
        "Assign a handful of working-age characters to work in the village's "
        "non-residential buildings (granary, inn, mill, bakery, hall, market, "
        "communal, field_shelter). "
        "Not every character gets a job - children and elders are excluded, "
        "and each building only takes on 2-3 workers, scoped to its own "
        "population centre."
    )

    def handle(self, *args, **options):
        work_buildings = list(
            Building.objects.filter(building_type__in=WORK_BUILDING_TYPES)
        )
        if not work_buildings:
            self.stdout.write(self.style.WARNING("No work buildings found"))
            return

        assigned_ids: set[int] = set()

        for building in work_buildings:
            if not building.nodes.exists():
                self.stdout.write(
                    self.style.WARNING(
                        f"Building {building.id} has no nodes – skipping work assignment"
                    )
                )
                continue

            eligible = [
                char
                for char in Character.objects.filter(
                    population_centre=building.population_centre,
                    building__isnull=False,
                )
                if char.id not in assigned_ids
                and MIN_WORKING_AGE <= (char.get_age() // 365) <= MAX_WORKING_AGE
            ]
            if not eligible:
                continue

            slots = random.randint(MIN_WORKERS_PER_BUILDING, MAX_WORKERS_PER_BUILDING)
            workers = random.sample(eligible, min(slots, len(eligible)))

            for char in workers:
                char.assign_work(building)
                assigned_ids.add(char.id)
                self.stdout.write(
                    f"{char.full_name} now works at {building.name} (ID {building.id})"
                )

        self.stdout.write(self.style.SUCCESS("Workers have been assigned"))
