import json
import random
from math import sqrt

from django.contrib.gis.geos import Point
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError

from locations.models import PopulationCentre
from locations.services.population_centre_admin import delete_population_centre
from locations.services.road_connections import connect_nearest_village_roads
from locations.services.watabou_import import import_watabou_village
from locations.village_names import VILLAGE_NAMES


def _distance(p1: Point, p2: Point) -> float:
    return sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2)


class Command(BaseCommand):
    help = "Import a watabou city/village-generator JSON export as a PopulationCentre."

    def add_arguments(self, parser):
        parser.add_argument("file", help="Path to the exported watabou .json file")
        parser.add_argument(
            "--name",
            help="Name to give the new PopulationCentre (defaults to a random "
            "unused name from village_names.VILLAGE_NAMES, e.g. 'Driftmoor "
            "village')",
        )
        parser.add_argument(
            "--min-distance",
            type=int,
            default=1000,
            help="Minimum distance (metres) to keep from every existing PopulationCentre",
        )
        parser.add_argument(
            "--grid-size",
            type=int,
            default=10000,
            help="Half-width (metres) of the square region to search for a free spot",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="If a PopulationCentre with this name already exists, delete it "
            "(and its buildings/roads/nodes) and re-import at its old location "
            "instead of erroring. Prompts for confirmation unless --noinput is "
            "also passed.",
        )
        parser.add_argument(
            "--noinput",
            "--no-input",
            action="store_false",
            dest="interactive",
            help="Skip the --overwrite confirmation prompt (for scripting).",
        )

    def handle(self, *args, **options):
        with open(options["file"]) as fh:
            data = json.load(fh)

        name = options["name"] or self._pick_village_name()
        overwrite = options["overwrite"]

        if not overwrite and PopulationCentre.objects.filter(name=name).exists():
            raise CommandError(
                f"A PopulationCentre named '{name}' already exists. "
                "Pass --overwrite to replace it."
            )

        reimport_origin = None
        if overwrite:
            reimport_origin = self._delete_existing(name, options["interactive"])

        existing_locations = list(
            PopulationCentre.objects.exclude(name=name).values_list(
                "location", flat=True
            )
        )
        origin = reimport_origin or self._pick_origin(
            existing_locations, options["min_distance"], options["grid_size"]
        )

        try:
            population_centre = import_watabou_village(data, name=name, origin=origin)
        except IntegrityError as exc:
            if overwrite and PopulationCentre.objects.filter(name=name).exists():
                # Another process (or an unexpected race) recreated the same-name
                # centre between delete and import; remove it and retry once.
                self.stdout.write(
                    self.style.WARNING(
                        f"Name collision detected while importing '{name}'. "
                        "Retrying overwrite once..."
                    )
                )
                retry_origin = self._delete_existing(name, interactive=False) or origin
                population_centre = import_watabou_village(
                    data,
                    name=name,
                    origin=retry_origin,
                )
            else:
                raise CommandError(
                    f"Could not import '{name}' due to a duplicate name. "
                    "If replacing an existing centre, pass --overwrite."
                ) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported '{population_centre.name}' at {origin} "
                f"({population_centre.buildings.count()} buildings, "
                f"{population_centre.roads.count()} roads)"
            )
        )

        call_command("generate_paths", centre=population_centre.id)
        self.stdout.write(self.style.SUCCESS("Generated paths for the new centre"))

        connector = connect_nearest_village_roads(population_centre)
        if connector:
            self.stdout.write(
                self.style.SUCCESS(
                    "Connected roads to the nearest neighbouring village"
                )
            )

    def _delete_existing(self, name: str, interactive: bool) -> Point | None:
        """If a PopulationCentre called `name` exists, confirm, delete it, and
        return its old location so the caller can re-import in the same spot."""
        try:
            existing = PopulationCentre.objects.get(name=name)
        except PopulationCentre.DoesNotExist:
            return None

        if interactive:
            confirm = input(
                f"This will delete the existing PopulationCentre '{name}' "
                f"({existing.buildings.count()} buildings, "
                f"{existing.roads.count()} roads) and everything in it. "
                "Continue? [y/N] "
            )
            if confirm.strip().lower() not in ("y", "yes"):
                raise CommandError("Aborted - existing village was not deleted.")

        old_location = delete_population_centre(name)
        self.stdout.write(self.style.WARNING(f"Deleted existing '{name}'"))
        return old_location

    def _pick_village_name(self) -> str:
        used_names = set(PopulationCentre.objects.values_list("name", flat=True))
        available = [
            f"{village_name} village"
            for village_name in VILLAGE_NAMES
            if f"{village_name} village" not in used_names
        ]
        if not available:
            raise CommandError(
                "Every name in village_names.VILLAGE_NAMES is already taken - "
                "pass --name explicitly."
            )
        return random.choice(available)

    def _pick_origin(
        self, existing_locations: list[Point], min_distance: int, grid_size: int
    ) -> Point:
        for _ in range(200):
            candidate = Point(
                random.randint(-grid_size, grid_size),
                random.randint(-grid_size, grid_size),
                srid=3857,
            )
            if all(
                _distance(candidate, loc) >= min_distance for loc in existing_locations
            ):
                return candidate
        raise CommandError(
            "Could not find a free spot for the new village after 200 attempts - "
            "try a larger --grid-size or a smaller --min-distance."
        )
