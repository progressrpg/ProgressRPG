from django.core.management.base import BaseCommand
from locations.models import Building, InteriorSpace
from django.contrib.gis.geos import Polygon

USAGES = ["sleeping", "living", "cooking", "hygiene"]
STORAGE_PROPORTION = 0.08  # 8% of total footprint


class Command(BaseCommand):
    help = "Create interior spaces for existing buildings"

    def add_arguments(self, parser):
        parser.add_argument(
            "--centre", type=str, help="Limit to a specific population centre name"
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Delete existing interior spaces before regenerating",
        )

    def handle(self, *args, **options):
        centre_name = options.get("centre")
        overwrite = options.get("overwrite")

        buildings = Building.objects.all()
        if centre_name:
            buildings = buildings.filter(centre__name=centre_name)

        self.stdout.write(
            self.style.SUCCESS(f"Processing {buildings.count()} buildings...")
        )

        for building in buildings:
            self.create_interiors_for_building(building, overwrite)

        self.stdout.write(self.style.SUCCESS("Done!"))

    # ------------------------------------------------------

    def create_interiors_for_building(self, building, overwrite=False):
        if overwrite:
            building.interiorspaces.all().delete()

        building_area = building.footprint.area if building.footprint else 5.0
        subspaces_info = self.generate_subspaces(building_area)

        for info in subspaces_info:
            InteriorSpace.objects.create(
                building=building,
                usage=info["usage"],
                area=info["area"],
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {len(subspaces_info)} interior spaces for building {building.name}"
            )
        )

    # ------------------------------------------------------

    def generate_subspaces(self, building_area: float):
        storage_area = building_area * STORAGE_PROPORTION
        remaining_area = building_area - storage_area

        per_main_area = remaining_area / len(USAGES)

        subspaces = [{"usage": u, "area": per_main_area} for u in USAGES]

        subspaces.append({"usage": "storage", "area": storage_area})

        return subspaces
