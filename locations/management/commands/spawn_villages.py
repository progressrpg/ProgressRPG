import random
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point, Polygon
from locations.models import PopulationCentre, Building
from math import sqrt


def distance(p1: Point, p2: Point):
    """Euclidean distance between two Points."""
    dx = p1.x - p2.x
    dy = p1.y - p2.y
    return sqrt(dx * dx + dy * dy)


def create_building_footprint(center: Point, size=2):
    """Return a square polygon around the building location."""
    x, y = center.x, center.y
    half = size / 2
    return Polygon(
        (
            (x - half, y - half),
            (x - half, y + half),
            (x + half, y + half),
            (x + half, y - half),
            (x - half, y - half),  # close the ring
        )
    )


def create_centre_boundary(buildings: list[Point], padding=5):
    """Return a polygon roughly surrounding all buildings."""
    if not buildings:
        return None

    xs = [b.x for b in buildings]
    ys = [b.y for b in buildings]

    min_x, max_x = min(xs) - padding, max(xs) + padding
    min_y, max_y = min(ys) - padding, max(ys) + padding

    return Polygon(
        (
            (min_x, min_y),
            (min_x, max_y),
            (max_x, max_y),
            (max_x, min_y),
            (min_x, min_y),  # close the ring
        )
    )


class Command(BaseCommand):
    help = "Spawn population centres with buildings clustered around them, with footprints and boundaries"

    def add_arguments(self, parser):
        parser.add_argument("--num-centres", type=int, default=2)
        parser.add_argument("--buildings-per-centre", type=int, default=8)
        parser.add_argument("--grid-size", type=int, default=5000)
        parser.add_argument("--min-distance", type=int, default=3)

    def attempt_place_centre(self, centres_positions, min_distance=1000, max_distance=2000):
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

    def attempt_place_building(self, centre_point: Point, placed_buildings, min_distance)
        offset_x = random.randint(-5, 5)
        offset_y = random.randint(-5, 5)
        candidate = Point(centre_point.x + offset_x, centre_point.y + offset_y)
        
        if all(
            distance(candidate, bp) >= min_distance
            for bp in placed_buildings
        ):
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
                    min_centre_distance=1000,
                    max_centre_distance=2000
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

            centre_name =  f"Village {i+1}-{random.randint(1000,9999)}"

            # Place buildings around this centre
            placed_buildings = []
            for j in range(buildings_per_centre):
                for attempt in range(100):
                    building_point = self.attempt_place_building(new_point, placed_buildings, min_distance)
                    if building_point:
                        break

                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Could not place building {j+1} in {centre_name} after 100 attempts"
                        )
                    )
                    continue

                footprint = create_building_footprint(building_point)
                building_name = f"Building {j+1} ({centre_name})"
                Building.objects.create(
                    name=building_name,
                    location=building_point,
                    footprint=footprint,
                    population_centre=None,
                )
                placed_buildings.append(building_point)
                self.stdout.write(f"  Placed {building_name} at {building_point}")

            boundary = create_centre_boundary(placed_buildings)

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
