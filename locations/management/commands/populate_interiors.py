from django.core.management.base import BaseCommand
from locations.models import Building, InteriorSpace, Node
from django.contrib.gis.geos import Polygon, Point
from locations.models import Path
import random

from locations.utils import create_hub_and_spoke

BUILDING_INTERIORS_PROPORTIONS = {
    "residential": {
        "living": 0.25,
        "sleeping": 0.40,
        "kitchen": 0.20,
        "hygiene": 0.10,
        "storage": 0.05,
    },
    "granary": {
        "storage": 1.0,
    },
    "inn": {
        "sleeping": 0.50,
        "living": 0.20,
        "kitchen": 0.15,
        "storage": 0.15,
    },
    "mill": {
        "workshop": 0.70,
        "storage": 0.30,
    },
    "bakery": {
        "workshop": 0.50,
        "storage": 0.30,
        "living": 0.20,
    },
    "communal": {
        "meeting": 0.50,
        "kitchen": 0.30,
        "storage": 0.20,
    },
}

VILLAGE_SPECIAL_BUILDINGS = ["granary", "inn", "mill", "bakery", "communal"]
RESIDENTIAL_PER_VILLAGE = 5


class Command(BaseCommand):
    help = "Create interior spaces for existing buildings"

    def add_arguments(self, parser):
        parser.add_argument(
            "--centre", type=str, help="Limit to a specific population centre name"
        )

    def handle(self, *args, **options):
        centre_name = options.get("centre")

        buildings = Building.objects.all()
        if centre_name:
            buildings = buildings.filter(centre__name=centre_name)

        self.stdout.write(
            self.style.SUCCESS(f"Processing {buildings.count()} buildings...")
        )

        for building in buildings:
            nodes = self.create_interiors_for_building(building)
            central_node = building.node.filter(kind=Node.Kind.BUILDING).first()

            if central_node:
                paths = create_hub_and_spoke(self, central_node, nodes)

            for p in paths:
                p.population_centre = building.population_centre
            Path.objects.bulk_update(paths, ["population_centre"])

            entrance_node = building.node.filter(
                kind=Node.Kind.BUILDING_ENTRANCE
            ).first()
            if entrance_node:
                for node in nodes:
                    Path.objects.get_or_create(
                        from_node=entrance_node, to_node=central_node
                    )
                    Path.objects.get_or_create(
                        from_node=central_node, to_node=entrance_node
                    )

        self.stdout.write(self.style.SUCCESS("Done!"))

    # ------------------------------------------------------

    def create_interiors_for_building(self, building: Building):
        building.interiorspaces.all().delete()

        building_area = building.footprint.area if building.footprint else 5.0
        subspaces_info = self.generate_subspaces(building_area, building.building_type)

        if building.footprint:
            minx, miny, maxx, maxy = building.footprint.extent
        else:
            minx = miny = 0
            maxx = maxy = 5

        nodes = []
        for info in subspaces_info:
            name = info["usage"]
            space = InteriorSpace.objects.create(
                building=building,
                name=f"{name} of {building.name}",
                usage=info["usage"],
                area=info["area"],
            )

            node = self.random_point_in_polygon(
                building.footprint, minx, miny, maxx, maxy
            )

            node.interior_space = space
            # Don't set building here to avoid circular FK issues
            # node.building = building
            node.save(update_fields=["interior_space", "building"])
            nodes.append(node)

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {len(subspaces_info)} interior spaces for building {building.name}"
            )
        )
        return nodes

    # ------------------------------------------------------

    def random_point_in_polygon(
        self, polygon, minx, miny, maxx, maxy, max_attempts=50, node_kwargs=None
    ) -> Node:
        """
        Generate a random Point inside the given polygon.
        """
        if node_kwargs is None:
            node_kwargs = {}

        if not polygon:
            return Node.objects.create(
                location=Point(0, 0, srid=3857),
                kind=Node.Kind.INTERIOR,
                **node_kwargs,
            )

        for _ in range(max_attempts):
            x = random.uniform(minx, maxx)
            y = random.uniform(miny, maxy)
            p = Point(x, y, srid=3857)

            if polygon.contains(p):
                return Node.objects.create(
                    name="Interior Node",
                    location=p,
                    kind=Node.Kind.INTERIOR,
                    **node_kwargs,
                )

        # fallback: return centroid if random sampling fails
        return Node.objects.create(
            location=polygon.centroid,
            kind=Node.Kind.INTERIOR,
            **node_kwargs,
        )

    # ------------------------------------------------------

    def generate_subspaces(self, building_area: float, building_type: str):
        proportions = BUILDING_INTERIORS_PROPORTIONS.get(building_type, {"other": 1.0})
        subspaces = []

        for usage, fraction in proportions.items():
            area = building_area * fraction
            subspaces.append({"usage": usage, "area": area})

        return subspaces
