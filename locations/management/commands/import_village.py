import json

from django.contrib.gis.geos import Point
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError

from locations.models import PopulationCentre
from locations.services.population_centre_admin import delete_population_centre
from locations.services.road_connections import connect_nearest_village_roads
from locations.services.watabou_import import import_watabou_village
from locations.village_layout import VILLAGE_LAYOUT
from locations.village_names import VILLAGE_NAMES


class Command(BaseCommand):
    help = "Import a watabou city/village-generator JSON export as a PopulationCentre."

    def add_arguments(self, parser):
        parser.add_argument("file", help="Path to the exported watabou .json file")
        parser.add_argument(
            "--name",
            help="Name to give the new PopulationCentre (defaults to the first "
            "unused name from village_names.VILLAGE_NAMES, e.g. 'Driftmoor "
            "village')",
        )
        parser.add_argument(
            "--x",
            type=int,
            help="Origin X coordinate (metres, SRID 3857) to centre the village on. "
            "Pass both --x and --y together, or omit both to auto-pick the "
            "first unoccupied village_layout.VILLAGE_LAYOUT slot (ignored if "
            "--overwrite ends up reusing an existing centre's location).",
        )
        parser.add_argument(
            "--y",
            type=int,
            help="Origin Y coordinate (metres, SRID 3857) to centre the village on. "
            "Pass both --x and --y together, or omit both to auto-pick the "
            "first unoccupied village_layout.VILLAGE_LAYOUT slot (ignored if "
            "--overwrite ends up reusing an existing centre's location).",
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

        origin = reimport_origin or self._resolve_origin(options["x"], options["y"])

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

        # Watabou exports carry their own "crops" Subzone geometry (see
        # watabou_import._import_fields), but not a field_shelter Building or
        # FieldCrop - generate_fields attaches those. Must run before
        # generate_paths, which needs the shelter's entrance node to exist.
        call_command("generate_fields")
        self.stdout.write(self.style.SUCCESS("Generated fields for the new centre"))

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
        for village_name in VILLAGE_NAMES:
            candidate = f"{village_name} village"
            if candidate not in used_names:
                return candidate
        raise CommandError(
            "Every name in village_names.VILLAGE_NAMES is already taken - "
            "pass --name explicitly."
        )

    def _resolve_origin(self, x: int | None, y: int | None) -> Point:
        if x is None and y is None:
            return self._pick_unused_layout_slot()
        if x is None or y is None:
            raise CommandError(
                "Pass both --x and --y together for the village's origin, or "
                "neither to auto-pick an unoccupied village_layout.VILLAGE_LAYOUT "
                "slot."
            )
        return Point(x, y, srid=3857)

    def _pick_unused_layout_slot(self) -> Point:
        """
        First VILLAGE_LAYOUT slot with no existing PopulationCentre already
        sitting on it - lets an ad-hoc import (e.g. trying out a village file
        outside locations/data/, so outside the setup_world/import_villages
        pipeline) claim spare grid space without hand-picking coordinates.

        Not persistent across a setup_world rerun: that command deletes every
        existing PopulationCentre before reimporting only locations/data/'s
        files (see setup_world.py), so an ad-hoc import placed here will need
        to be redone afterwards - and may land on a different free slot next
        time, since which slots are "unoccupied" depends on whatever other
        centres exist at that moment.
        """
        occupied = {
            (round(centre.location.x), round(centre.location.y))
            for centre in PopulationCentre.objects.only("location")
        }
        for x, y in VILLAGE_LAYOUT:
            if (x, y) not in occupied:
                return Point(x, y, srid=3857)
        raise CommandError(
            f"Every village_layout.VILLAGE_LAYOUT slot ({len(VILLAGE_LAYOUT)}) is "
            "already occupied by a PopulationCentre - pass --x/--y explicitly, "
            "or add more slots (GRID_COLUMNS/GRID_ROWS)."
        )
