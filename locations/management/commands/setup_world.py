from django.core.management import BaseCommand, call_command


class Command(BaseCommand):
    help = "Run the full world setup pipeline, keeping existing characters."

    def handle(self, *args, **options):
        self.stdout.write("=== Spawning villages ===")
        call_command("spawn_villages")

        self.stdout.write("=== Populating interiors ===")
        call_command("populate_interiors")

        self.stdout.write("=== Generating points ===")
        call_command("generate_points")

        self.stdout.write("=== Generating paths ===")
        call_command("generate_paths")

        self.stdout.write("=== Placing characters ===")
        call_command("place_characters")

        self.stdout.write("=== Generating land areas ===")
        call_command("generate_landarea")

        self.stdout.write(self.style.SUCCESS("All setup tasks completed!"))
