import random
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point, Polygon, MultiPolygon
from django.contrib.gis.db.models.functions import Distance
from locations.models import PopulationCentre, Building, InteriorSpace, Node, Path
from math import sqrt


SPECIAL_BUILDINGS = ["granary", "inn", "mill", "bakery", "communal"]
RESIDENTIAL_PER_VILLAGE = 5


def distance(p1: Point, p2: Point):
    """Euclidean distance between two Points."""
    dx = p1.x - p2.x
    dy = p1.y - p2.y
    return sqrt(dx * dx + dy * dy)


def create_building_footprint(centre: Point, min_size=5, max_size=20, irregularity=0.3):
    """Return a polygon around the building location with variation."""
    if not centre:
        raise ValueError(f"create_building_footprint needs Point to exist!")

    x, y = centre.x, centre.y

    width = random.uniform(min_size, max_size)
    height = random.uniform(min_size, max_size)

    hw, hh = width / 2, height / 2

    corners = [
        (x - hw, y - hh),
        (x - hw, y + hh),
        (x + hw, y + hh),
        (x + hw, y - hh),
    ]

    if irregularity > 0:
        max_dx = width * irregularity
        max_dy = height * irregularity
        corners = [
            (cx + random.uniform(-max_dx, max_dx), cy + random.uniform(-max_dy, max_dy))
            for cx, cy in corners
        ]

    corners.append(corners[0])

    return Polygon(corners)


def create_centre_boundary(buildings: list[Polygon], padding=10):
    """Return a polygon roughly surrounding all building footprints."""
    if not buildings:
        return None

    multi = MultiPolygon(buildings)
    hull = multi.convex_hull
    return hull.buffer(padding)


class Command(BaseCommand):
    help = "Spawn population centres with buildings clustered around them, with footprints and boundaries"

    def add_arguments(self, parser):
        parser.add_argument("--num-centres", type=int, default=2)
        parser.add_argument("--grid-size", type=int, default=5000)
        parser.add_argument("--min-distance", type=int, default=3)

    def attempt_place_centre(
        self, centres_positions, grid_size=5000, min_distance=1000, max_distance=2000
    ):
        x = random.randint(0, grid_size)
        y = random.randint(0, grid_size)
        new_point = Point(x, y)

        if not centres_positions:
            return new_point

        for cp in centres_positions:
            d = distance(new_point, cp)

            if d < min_distance or d > max_distance:
                return False

        return new_point

    def attempt_place_building(
        self, centre_point: Point, placed_buildings, min_distance
    ):
        offset_x = random.randint(-5, 5)
        offset_y = random.randint(-5, 5)
        candidate = Point(centre_point.x + offset_x, centre_point.y + offset_y)

        if all(distance(candidate, bp) >= min_distance for bp in placed_buildings):
            return candidate

        return None

    def create_street_network(self, central_node, building_nodes, max_neighbours=2):
        """
        Connects building nodes to each other to create 'streets',
        while keeping connections to the central node.
        """
        paths = []
        # 1 Keep hub-and-spoke connections
        for node in building_nodes:
            if node == central_node:
                continue
            path1, _ = Path.objects.get_or_create(from_node=node, to_node=central_node)
            path2, _ = Path.objects.get_or_create(from_node=central_node, to_node=node)
            paths.extend([path1, path2])

        # Connect each building node to its nearest neighbours
        for node in building_nodes:
            if node == central_node:
                continue

            # Exclude itself and the central node
            candidates = [
                n for n in building_nodes if n.pk not in (node.pk, central_node.pk)
            ]

            # Annotate distances and sort
            nearest = sorted(
                candidates, key=lambda n: node.location.distance(n.location)
            )[:max_neighbours]

            for neighbour in nearest:
                # Avoid duplicate paths
                path1, _ = Path.objects.get_or_create(from_node=node, to_node=neighbour)
                path2, _ = Path.objects.get_or_create(from_node=neighbour, to_node=node)
                paths.extend([path1, path2])

        return paths

    def handle(self, *args, **options):
        PopulationCentre.objects.all().delete()
        Building.objects.all().delete()
        InteriorSpace.objects.all().delete()
        Node.objects.all().delete()
        Path.objects.all().delete()
        self.stdout.write("Deleted all existing game world locations")

        num_centres = options["num_centres"]
        grid_size = options["grid_size"]
        min_distance = options["min_distance"]

        centres_positions = []
        # Place centres
        for i in range(num_centres):
            for attempt in range(100):
                result = self.attempt_place_centre(
                    centres_positions,
                    grid_size=5000,
                    min_centre_distance=1000,
                    max_centre_distance=2000,
                )
                if result:
                    new_point = result
                    break
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"Could not place centre {i+1} after 100 attempts"
                    )
                )
                continue
            centre_name = f"Village {i+1}-{random.randint(1000,9999)}"

            # Place buildings around this centre
            residential_buildings = [
                f"residential-{i+1}" for i in range(RESIDENTIAL_PER_VILLAGE)
            ]
            all_buildings_to_place = SPECIAL_BUILDINGS + residential_buildings

            placed_buildings = []
            placed_footprints = []
            created_nodes = []

            for btype_or_name in all_buildings_to_place:
                for attempt in range(100):
                    building_point = self.attempt_place_building(
                        new_point, placed_buildings, min_distance
                    )

                    if building_point is None:
                        continue

                    footprint = create_building_footprint(
                        building_point, min_size=10, max_size=25, irregularity=0.1
                    )
                    if all(
                        not footprint.intersects(existing_fp)
                        for existing_fp in placed_footprints
                    ):
                        if btype_or_name in SPECIAL_BUILDINGS:
                            building_name = (
                                f"{btype_or_name.capitalize()} of ({centre_name})"
                            )
                            building_type = btype_or_name
                        else:
                            building_name = f"House {btype_or_name.split('-')[1]} of ({centre_name})"
                            building_type = "residential"

                        placed_footprints.append(footprint)
                        building = Building.objects.create(
                            name=building_name,
                            building_type=building_type,
                            location=building_point,
                            footprint=footprint,
                            population_centre=None,
                        )

                        node, _ = Node.objects.get_or_create(
                            building=building,
                            defaults={
                                "name": f"Node for {building.name}",
                                "location": building.location,
                                "population_centre": building.population_centre,
                            },
                        )

                        placed_buildings.append(building_point)
                        created_nodes.append(node)
                        self.stdout.write(
                            f"  Placed {building_name} at {building_point}"
                        )
                        break

                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Could not place building {btype_or_name} in {centre_name} after 100 attempts"
                        )
                    )
                    continue

            boundary = create_centre_boundary(placed_footprints)

            centre = PopulationCentre.objects.create(
                name=centre_name, location=new_point, boundary=boundary
            )

            central_node, _ = Node.objects.get_or_create(
                name=f"Central node of settlement {centre.name}",
                population_centre=centre,
                location=centre.location,
            )

            paths = self.create_street_network(central_node, created_nodes)
            for path in paths:
                path.population_centre = centre
            Path.objects.bulk_update(paths, ["population_centre"])

            Building.objects.filter(location__in=placed_buildings).update(
                population_centre=centre
            )

            centres_positions.append(new_point)
            self.stdout.write(f"Created PopulationCentre: {centre_name} at {new_point}")

        self.stdout.write(
            self.style.SUCCESS("Finished spawning population centres with buildings")
        )
