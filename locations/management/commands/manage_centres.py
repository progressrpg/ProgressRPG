from django.core.management.base import BaseCommand, CommandError

from locations.models import PopulationCentre
from locations.services.population_centre_admin import delete_population_centre


class Command(BaseCommand):
    help = "List or delete existing PopulationCentres."

    def add_arguments(self, parser):
        parser.add_argument("action", choices=["list", "delete"])
        parser.add_argument(
            "--name", help="PopulationCentre name to delete (required for 'delete')"
        )
        parser.add_argument(
            "--noinput",
            "--no-input",
            action="store_false",
            dest="interactive",
            help="Skip the delete confirmation prompt (for scripting).",
        )

    def handle(self, *args, **options):
        if options["action"] == "list":
            self._list()
        else:
            self._delete(options["name"], options["interactive"])

    def _list(self):
        centres = PopulationCentre.objects.order_by("name")
        if not centres.exists():
            self.stdout.write("No PopulationCentres found.")
            return
        for centre in centres:
            self.stdout.write(
                f"{centre.name} - {centre.buildings.count()} buildings, "
                f"{centre.roads.count()} roads, at {centre.location}"
            )

    def _delete(self, name: str | None, interactive: bool):
        if not name:
            raise CommandError("--name is required for 'delete'")

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
