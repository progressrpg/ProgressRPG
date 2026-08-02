from pathlib import Path

from django.core.management import BaseCommand, call_command

# Watabou village exports committed for production use - see import_village.
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


class Command(BaseCommand):
    help = "Run the full world setup pipeline, keeping existing characters."

    def handle(self, *args, **options):
        village_files = sorted(DATA_DIR.glob("village*.json"))

        if village_files:
            self.stdout.write("=== Importing villages ===")
            for village_file in village_files:
                # No --name: import_village auto-picks an unused name from
                # village_names.VILLAGE_NAMES, same as spawn_villages does.
                call_command(
                    "import_village",
                    str(village_file),
                    overwrite=True,
                    interactive=False,
                )
        else:
            self.stdout.write("=== Spawning villages ===")
            call_command("spawn_villages", num_centres=1)

        self.stdout.write("=== Placing characters ===")
        call_command("place_characters")

        # Imported villages already have real field geometry from the
        # watabou export (see watabou_import._import_fields) -
        # generate_landarea unconditionally deletes and procedurally
        # regenerates land/fields for every population centre, which would
        # destroy that imported geometry, so it's skipped in that case.
        if not village_files:
            self.stdout.write("=== Generating land areas ===")
            # Must run before generate_fields, which attaches each FieldCrop to
            # the "crops" Subzone this creates - only needs boundary/location/
            # residents, all already set by spawn_villages.
            call_command("generate_landarea")

            self.stdout.write("=== Generating fields ===")
            # Must run before generate_paths, which needs the field shelter's
            # entrance node to exist.
            call_command("generate_fields")

        self.stdout.write("=== Generating points ===")
        call_command("generate_points")

        self.stdout.write("=== Generating paths ===")
        # Must run before populate_interiors: generate_paths deletes all
        # Path rows for the centre before rebuilding the street network, so
        # running it after populate_interiors would wipe out the
        # entrance<->interior connections that command creates.
        call_command("generate_paths")

        self.stdout.write("=== Populating interiors ===")
        call_command("populate_interiors")

        self.stdout.write("=== Assigning workers ===")
        call_command("assign_workers")

        self.stdout.write(self.style.SUCCESS("All setup tasks completed!"))
