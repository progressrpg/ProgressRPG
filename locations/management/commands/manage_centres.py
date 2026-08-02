from django.core.management.base import BaseCommand, CommandError

from locations.models import PopulationCentre
from locations.services.population_centre_admin import delete_population_centre


class Command(BaseCommand):
    help = "List or delete existing PopulationCentres."

    def add_arguments(self, parser):
        parser.add_argument(
            "--list", action="store_true", help="List existing PopulationCentres."
        )
        parser.add_argument(
            "--delete", metavar="NAME", help="Delete the PopulationCentre named NAME."
        )
        parser.add_argument(
            "--noinput",
            "--no-input",
            action="store_false",
            dest="interactive",
            help="Skip the --delete confirmation prompt (for scripting).",
        )

    def handle(self, *args, **options):
        if options["list"] and options["delete"]:
            raise CommandError("Pass only one of --list or --delete.")
        if options["delete"]:
            self._delete(options["delete"], options["interactive"])
        elif options["list"]:
            self._list()
        else:
            # print_help() writes straight to the real sys.stdout via
            # argparse, bypassing self.stdout - so a test capturing output
            # via call_command(stdout=...) would see nothing. Writing the
            # formatted help text through self.stdout instead keeps it
            # testable the same way every other branch here is.
            self.stdout.write(
                self.create_parser("manage.py", "manage_centres").format_help()
            )

    def _list(self):
        centres = PopulationCentre.objects.order_by("name")
        count = centres.count()
        if not centres.exists():
            self.stdout.write("No PopulationCentres found.")
            return
        self.stdout.write(f"Found {count} PopulationCentres:")
        for centre in centres:
            self.stdout.write(
                f"{centre.name} - {centre.buildings.count()} buildings, "
                f"{centre.roads.count()} roads, at {centre.location}"
            )

    def _delete(self, name: str, interactive: bool):
        try:
            existing = PopulationCentre.objects.get(name=name)
        except PopulationCentre.DoesNotExist:
            raise CommandError(f"No PopulationCentre named '{name}' found.")

        if interactive:
            confirm = input(
                f"This will delete PopulationCentre '{name}' "
                f"({existing.buildings.count()} buildings, "
                f"{existing.roads.count()} roads) and everything in it. "
                "Continue? [y/N] "
            )
            if confirm.strip().lower() not in ("y", "yes"):
                raise CommandError("Aborted - nothing was deleted.")

        delete_population_centre(name)
        self.stdout.write(self.style.SUCCESS(f"Deleted '{name}'"))
