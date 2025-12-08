import random
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point, Polygon, MultiPolygon
from locations.models import PopulationCentre, Building
from math import sqrt


def distance(p1: Point, p2: Point):
    """Euclidean distance between two Points."""
    dx = p1.x - p2.x
    dy = p1.y - p2.y
    return sqrt(dx * dx + dy * dy)


def create_building_footprint(centre: Point, min_size=5, max_size=20, irregularity=0.3):
    """Return a polygon around the building location with variation."""
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
        parser.add_argument("--buildings-per-centre", type=int, default=8)
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
        offset_x = random.randint(-50, 50)
        offset_y = random.randint(-50, 50)
        candidate = Point(centre_point.x + offset_x, centre_point.y + offset_y)

        if all(distance(candidate, bp) >= min_distance for bp in placed_buildings):
            return candidate

        return None

    def handle(self, *args, **options):
        PopulationCentre.objects.all().delete()
        Building.objects.all().delete()
        self.stdout.write("Deleted all existing population centres and buildings")

        num_centres = options["num_centres"]
        buildings_per_centre = options["buildings_per_centre"]
        grid_size = options["grid_size"]
        min_distance = options["min_distance"]

        centres_positions = []
        # Place centres
        for i in range(num_centres):
            for attempt in range(100):
                result = self.attempt_place_centre(
                    centres_positions,
                    grid_size=grid_size,
                    min_distance=1000,
                    max_distance=2000,
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
            placed_buildings = []
            placed_footprints = []
            for j in range(buildings_per_centre):
                for attempt in range(100):
                    building_point = self.attempt_place_building(
                        new_point, placed_buildings, min_distance
                    )

                    footprint = create_building_footprint(
                        building_point, min_size=10, max_size=25, irregularity=0.2
                    )
                    if all(
                        not footprint.intersects(existing_fp)
                        for existing_fp in placed_footprints
                    ):
                        building_name = f"Building {j+1} ({centre_name})"
                        placed_footprints.append(footprint)
                        Building.objects.create(
                            name=building_name,
                            location=building_point,
                            footprint=footprint,
                            population_centre=None,
                        )
                        placed_buildings.append(building_point)
                        self.stdout.write(
                            f"  Placed {building_name} at {building_point}"
                        )
                        break

                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Could not place building {j+1} in {centre_name} after 100 attempts"
                        )
                    )
                    continue

            boundary = create_centre_boundary(placed_footprints)

            centre = PopulationCentre.objects.create(
                name=centre_name, location=new_point, boundary=boundary
            )

            Building.objects.filter(location__in=placed_buildings).update(
                population_centre=centre
            )

            centres_positions.append(new_point)
            self.stdout.write(f"Created PopulationCentre: {centre_name} at {new_point}")

        self.stdout.write(
            self.style.SUCCESS("Finished spawning population centres with buildings")
        )
