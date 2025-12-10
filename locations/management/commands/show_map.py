from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from locations.models import Building, PopulationCentre, LandArea
from character.models import Character
from math import sqrt


def distance(p1, p2):
    """Euclidean distance between two Points"""
    dx = p1.x - p2.x
    dy = p1.y - p2.y
    return sqrt(dx * dx + dy * dy)


class Command(BaseCommand):
    help = "Display a simple ASCII map for a chosen village"

    def add_arguments(self, parser):
        parser.add_argument(
            "--size",
            type=int,
            default=40,
            help="The dimensions of the map (default: 40)",
        )
        parser.add_argument(
            "--show-landarea",
            action="store_true",
            help="Display the population centre's land areas",
        )

    def handle(self, *args, **options):
        map_size = options["size"]
        show_landarea = options["show_landarea"]

        centres = PopulationCentre.objects.all()
        if not centres.exists():
            self.stdout.write(self.style.WARNING("No PopulationCentres found."))
            return

        self.stdout.write("Available villages:")
        for idx, centre in enumerate(centres, start=1):
            self.stdout.write(f"{idx}. {centre.name}")

        selected_centre = self.choose_centre(centres)
        self.stdout.write(f"Displaying village: {selected_centre.name}")

        buildings = Building.objects.filter(population_centre=selected_centre)
        characters = [
            c
            for c in Character.objects.all()
            if getattr(c, "location", None)
            and self.distance(c.location, selected_centre.location) <= map_size
        ]

        all_points = self.collect_all_points(buildings, characters, selected_centre)
        if show_landarea:
            landareas = LandArea.objects.filter(population_centre=selected_centre)
            for la in landareas:
                if getattr(la, "area_polygon", None):
                    minx, miny, maxx, maxy = la.area_polygon.extent
                    all_points.extend([Point(minx, miny), Point(maxx, maxy)])
        else:
            landareas = []

        if not all_points:
            self.stdout.write("No locations to display for this village.")
            return

        min_x, min_y, scale_x, scale_y = self.compute_grid_bounds(all_points, map_size)
        grid = self.create_empty_grid(map_size)

        if getattr(selected_centre, "boundary", None):
            self.plot_polygon(
                grid, selected_centre.boundary, min_x, min_y, scale_x, scale_y, map_size
            )

        # Plot land areas first so buildings/characters overwrite them
        if show_landarea:
            for la in landareas:
                if getattr(la, "area_polygon", None):
                    self.plot_polygon(
                        grid,
                        la.area_polygon,
                        min_x,
                        min_y,
                        scale_x,
                        scale_y,
                        map_size,
                        symbol="L",
                    )

        self.plot_buildings(grid, buildings, min_x, min_y, scale_x, scale_y, map_size)
        self.plot_characters(grid, characters, min_x, min_y, scale_x, scale_y, map_size)

        for row in reversed(grid):
            self.stdout.write(" ".join(row))

    # ------------------- Helper methods -------------------

    def distance(self, p1: Point, p2: Point) -> float:
        """Euclidean distance between two Points"""
        dx = p1.x - p2.x
        dy = p1.y - p2.y
        return sqrt(dx * dx + dy * dy)

    def choose_centre(self, centres):
        while True:
            choice = input("Enter the number of the village to display: ")
            try:
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(centres):
                    return centres[choice_idx]
            except ValueError:
                pass
            self.stdout.write("Invalid choice. Try again.")

    def collect_all_points(self, buildings, characters, centre):
        points = [b.location for b in buildings if b.location] + [
            c.location for c in characters if c.location
        ]
        for b in buildings:
            if getattr(b, "footprint", None):
                minx, miny, maxx, maxy = b.footprint.extent
                points.extend([Point(minx, miny), Point(maxx, maxy)])
        if getattr(centre, "boundary", None):
            minx, miny, maxx, maxy = centre.boundary.extent
            points.extend([Point(minx, miny), Point(maxx, maxy)])
        return points

    def compute_grid_bounds(self, points, map_size):
        min_x = min(p.x for p in points)
        max_x = max(p.x for p in points)
        min_y = min(p.y for p in points)
        max_y = max(p.y for p in points)
        dx = max_x - min_x + 1
        dy = max_y - min_y + 1
        scale_x = (map_size - 3) / dx if dx > 0 else 1
        scale_y = (map_size - 3) / dy if dy > 0 else 1
        return min_x, min_y, scale_x, scale_y

    def point_to_grid(self, p: Point, min_x, min_y, scale_x, scale_y, map_size):
        x = int((p.x - min_x) * scale_x) + 1
        y = int((p.y - min_y) * scale_y) + 1
        x = max(0, min(map_size - 1, x))
        y = max(0, min(map_size - 1, y))
        return x, y

    def create_empty_grid(self, map_size):
        return [["." for _ in range(map_size)] for _ in range(map_size)]

    def sample_polygon_edges(self, polygon, step=3.0):
        coords = list(polygon.coords[0])
        for i in range(len(coords) - 1):
            x1, y1 = coords[i]
            x2, y2 = coords[i + 1]
            dx, dy = x2 - x1, y2 - y1
            dist = (dx**2 + dy**2) ** 0.5
            num_points = max(int(dist / step), 1)
            for j in range(num_points):
                yield (x1 + dx * j / num_points, y1 + dy * j / num_points)

    def plot_polygon(
        self, grid, polygon, min_x, min_y, scale_x, scale_y, map_size, symbol="P"
    ):
        for x, y in self.sample_polygon_edges(polygon):
            gx, gy = self.point_to_grid(
                Point(x, y), min_x, min_y, scale_x, scale_y, map_size
            )
            if 0 <= gy < len(grid) and 0 <= gx < len(grid[0]):
                grid[gy][gx] = symbol

    def plot_buildings(self, grid, buildings, min_x, min_y, scale_x, scale_y, map_size):
        for b in buildings:
            if getattr(b, "footprint", None):
                minx, miny, maxx, maxy = b.footprint.extent
                gx_min, gy_min = self.point_to_grid(
                    Point(minx, miny), min_x, min_y, scale_x, scale_y, map_size
                )
                gx_max, gy_max = self.point_to_grid(
                    Point(maxx, maxy), min_x, min_y, scale_x, scale_y, map_size
                )
                for gx in range(gx_min, gx_max + 1):
                    for gy in range(gy_min, gy_max + 1):
                        grid[gy][gx] = "B"
            else:
                gx, gy = self.point_to_grid(
                    b.location, min_x, min_y, scale_x, scale_y, map_size
                )
                grid[gy][gx] = "B"

    def plot_characters(
        self, grid, characters, min_x, min_y, scale_x, scale_y, map_size
    ):
        for c in characters:
            gx, gy = self.point_to_grid(
                c.location, min_x, min_y, scale_x, scale_y, map_size
            )
            grid[gy][gx] = "C"
