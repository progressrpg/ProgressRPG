from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from locations.models import Building, PopulationCentre
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

    def handle(self, *args, **options):
        map_size = options["size"]

        # List all villages
        centres = PopulationCentre.objects.all()
        if not centres.exists():
            self.stdout.write(self.style.WARNING("No PopulationCentres found."))
            return

        self.stdout.write("Available villages:")
        for idx, centre in enumerate(centres, start=1):
            self.stdout.write(f"{idx}. {centre.name}")

        # Choose a village
        while True:
            choice = input("Enter the number of the village to display: ")
            try:
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(centres):
                    selected_centre = centres[choice_idx]
                    break
            except ValueError:
                pass
            self.stdout.write("Invalid choice. Try again.")

        self.stdout.write(f"Displaying village: {selected_centre.name}")

        # Filter buildings and characters for this village
        buildings = Building.objects.filter(population_centre=selected_centre)

        characters = []
        for c in Character.objects.all():
            if getattr(c, "location", None):
                if distance(c.location, selected_centre.location) <= map_size:
                    characters.append(c)

        # Gather all locations to compute grid scaling
        all_points = [b.location for b in buildings if b.location] + [
            c.location for c in characters if c.location
        ]

        # Include building footprints and centre boundary extents
        for b in buildings:
            if getattr(b, "footprint", None):
                minx, miny, maxx, maxy = b.footprint.extent
                all_points.extend([Point(minx, miny), Point(maxx, maxy)])
        if getattr(selected_centre, "boundary", None):
            minx, miny, maxx, maxy = selected_centre.boundary.extent
            all_points.extend([Point(minx, miny), Point(maxx, maxy)])

        if not all_points:
            self.stdout.write("No locations to display for this village.")
            return

        min_x = min(p.x for p in all_points)
        max_x = max(p.x for p in all_points)
        min_y = min(p.y for p in all_points)
        max_y = max(p.y for p in all_points)

        dx = max_x - min_x + 1
        dy = max_y - min_y + 1
        scale_x = (map_size - 3) / dx if dx > 0 else 1
        scale_y = (map_size - 3) / dy if dy > 0 else 1

        def to_grid(p):
            x = int((p.x - min_x) * scale_x) + 1
            y = int((p.y - min_y) * scale_y) + 1
            # Clamp to grid limits
            x = max(0, min(map_size - 1, x))
            y = max(0, min(map_size - 1, y))
            return x, y

        # Initialize empty grid
        grid = [["." for _ in range(map_size)] for _ in range(map_size)]

        # Plot centre boundary
        if getattr(selected_centre, "boundary", None):
            # Sample boundary polygon as grid points (roughly)
            for x, y in selected_centre.boundary.coords[0]:
                gx, gy = to_grid(Point(x, y))
                grid[gy][gx] = "P"

        # Plot building footprints
        for b in buildings:
            if getattr(b, "footprint", None):
                minx, miny, maxx, maxy = b.footprint.extent
                gx_min, gy_min = to_grid(Point(minx, miny))
                gx_max, gy_max = to_grid(Point(maxx, maxy))
                for gx in range(gx_min, gx_max + 1):
                    for gy in range(gy_min, gy_max + 1):
                        grid[gy][gx] = "B"
            else:
                gx, gy = to_grid(b.location)
                grid[gy][gx] = "B"

        # Plot characters
        for c in characters:
            gx, gy = to_grid(c.location)
            grid[gy][gx] = "C"

        # Print grid (y-axis inverted so top-left is 0,0)
        for row in reversed(grid):
            self.stdout.write(" ".join(row))
