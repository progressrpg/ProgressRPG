from django.core.management import BaseCommand, call_command


class Command(BaseCommand):
    help = (
        "Seed a single small village for the village view. Skips "
        "generate_landarea since it's not used by the decorative view, but "
        "does run generate_paths - the commute scheduler needs a real "
        "Node/Path graph to route characters between home and work."
    )

    def handle(self, *args, **options):
        self.stdout.write("=== Spawning village ===")
        call_command("generate_villages", num_centres=1)

        self.stdout.write("=== Generating fields ===")
        # Must run before generate_paths, which needs the field's entrance
        # node to exist to route it into the street network.
        call_command("generate_fields")

        self.stdout.write("=== Generating paths ===")
        # Must run before populate_interiors: generate_paths deletes all
        # Path rows for the centre before rebuilding the street network, so
        # running it after populate_interiors would wipe out the
        # entrance<->interior connections that command creates.
        call_command("generate_paths")

        self.stdout.write("=== Populating interiors ===")
        call_command("populate_interiors")

        self.stdout.write("=== Placing characters ===")
        call_command("place_characters")

        self.stdout.write("=== Assigning workers ===")
        call_command("assign_workers")

        self.stdout.write(self.style.SUCCESS("Village view seed data ready!"))
