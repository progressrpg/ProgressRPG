from django.core.management.base import BaseCommand
from locations.models import Building, PopulationCentre
from character.models import Character


class Command(BaseCommand):
    help = "Display a simple text-based grid for a chosen village"

    def add_arguments(self, parser):
        parser.add_argument(
            "--grid-size", type=int, default=40, help="Size of the grid (default: 40)"
        )

    def handle(self, *args, **options):
        grid_size = options["grid_size"]

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
            if c.position:
                dx = c.position.x - selected_centre.position.x
                dy = c.position.y - selected_centre.position.y
                distance = (dx * dx + dy * dy) ** 0.5
                if distance <= grid_size:
                    characters.append(c)

        # Gather all positions to compute grid scaling
        all_positions = [b.position for b in buildings if b.position] + [
            c.position for c in characters if c.position
        ]

        if not all_positions:
            self.stdout.write("No positions to display for this village.")
            return

        min_x = min(p.x for p in all_positions)
        max_x = max(p.x for p in all_positions)
        min_y = min(p.y for p in all_positions)
        max_y = max(p.y for p in all_positions)

        dx = max_x - min_x + 1
        dy = max_y - min_y + 1
        scale_x = (grid_size - 3) / dx if dx > 0 else 1
        scale_y = (grid_size - 3) / dy if dy > 0 else 1

        def to_grid(p):
            x = int((p.x - min_x) * scale_x) + 1
            y = int((p.y - min_y) * scale_y) + 1
            return x, y

        # Initialize empty grid
        grid = [["." for _ in range(grid_size)] for _ in range(grid_size)]

        # Plot buildings
        for b in buildings:
            x, y = to_grid(b.position)
            grid[y][x] = "B"

        # Plot characters
        for c in characters:
            x, y = to_grid(c.position)
            grid[y][x] = "C"

        # Print grid (y-axis inverted so top-left is 0,0)
        for row in reversed(grid):
            self.stdout.write(" ".join(row))
