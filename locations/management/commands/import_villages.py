from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from locations.village_layout import VILLAGE_LAYOUT
from locations.village_names import VILLAGE_NAMES

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


class Command(BaseCommand):
    help = (
        "Import every watabou village export in locations/data/, placing each "
        "one at a fixed slot from village_layout.VILLAGE_LAYOUT and naming it "
        "with the next unused entry from village_names.VILLAGE_NAMES - both in "
        "sorted filename order, so re-running the pipeline always produces the "
        "same layout instead of a random one."
    )

    def handle(self, *args, **options):
        village_files = sorted(DATA_DIR.glob("village*.json"))

        if len(village_files) > len(VILLAGE_LAYOUT):
            raise CommandError(
                f"{len(village_files)} village file(s) in {DATA_DIR}, but "
                f"village_layout.VILLAGE_LAYOUT only has {len(VILLAGE_LAYOUT)} "
                "slot(s) - add more slots (GRID_COLUMNS/GRID_ROWS) first."
            )

        if len(village_files) > len(VILLAGE_NAMES):
            raise CommandError(
                f"{len(village_files)} village file(s) in {DATA_DIR}, but "
                f"village_names.VILLAGE_NAMES only has {len(VILLAGE_NAMES)} "
                "name(s) - add more names first."
            )

        for index, village_file in enumerate(village_files):
            name = f"{VILLAGE_NAMES[index]} village"
            x, y = VILLAGE_LAYOUT[index]
            call_command(
                "import_village",
                str(village_file),
                name=name,
                x=x,
                y=y,
                overwrite=True,
                interactive=False,
            )
