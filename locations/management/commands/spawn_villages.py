import random
from django.core.management.base import BaseCommand
from locations.models import PopulationCentre, Building, Position
from math import sqrt


def distance(p1, p2):
    return sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2)


class Command(BaseCommand):
    help = "Spawn population centres with buildings clustered around them"

    def add_arguments(self, parser):
        parser.add_argument(
            "--num-centres", type=int, default=2, help="Number of population centres"
        )
        parser.add_argument(
            "--buildings-per-centre",
            type=int,
            default=8,
            help="Number of buildings per centre",
        )
        parser.add_argument(
            "--grid-size", type=int, default=5000, help="Max coordinate for x and y"
        )
        parser.add_argument(
            "--min-distance", type=int, default=3, help="Min distance between buildings"
        )
        parser.add_argument(
            "--min-centre-distance",
            type=int,
            default=1000,
            help="Min distance between population centres",
        )
        parser.add_argument(
            "--max-centre-distance",
            type=int,
            default=2000,
            help="Max distance between population centres",
        )

    def handle(self, *args, **options):
        PopulationCentre.objects.all().delete()
        Building.objects.all().delete()
        self.stdout.write("Deleted all existing population centres and buildings")

        num_centres = options["num_centres"]
        buildings_per_centre = options["buildings_per_centre"]
        grid_size = options["grid_size"]
        min_distance = options["min_distance"]
        min_centre_distance = options["min_centre_distance"]
        max_centre_distance = options["max_centre_distance"]

        centres_positions = []

        for i in range(num_centres):
            # Place centre respecting min and max distance from other centres
            for attempt in range(100):
                x = random.randint(0, grid_size)
                y = random.randint(0, grid_size)
                pos_ok = True

                for cp in centres_positions:
                    d = distance(Position(x=x, y=y), cp)
                    if d < min_centre_distance or d > max_centre_distance:
                        pos_ok = False
                        break

                if pos_ok or not centres_positions:
                    break
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"Could not place centre {i+1} after 100 attempts"
                    )
                )
                continue

            centre_pos = Position.objects.create(x=x, y=y)
            centre_name = f"Village {i+1}-{random.randint(1000,9999)}"
            centre = PopulationCentre.objects.create(
                name=centre_name, position=centre_pos
            )
            centres_positions.append(centre_pos)
            self.stdout.write(
                f"Created PopulationCentre: {centre_name} at {centre_pos}"
            )

            # Place buildings around this centre
            placed_buildings = []
            for j in range(buildings_per_centre):
                for attempt in range(100):
                    offset_x = random.randint(-5, 5)
                    offset_y = random.randint(-5, 5)
                    bx = centre_pos.x + offset_x
                    by = centre_pos.y + offset_y
                    # Check min distance from other buildings
                    if all(
                        sqrt((bx - px) ** 2 + (by - py) ** 2) >= min_distance
                        for px, py in placed_buildings
                    ):
                        break
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Could not place building {j+1} in {centre_name} after 100 attempts"
                        )
                    )
                    continue

                building_pos = Position.objects.create(x=bx, y=by)
                building_name = f"Building {j+1} ({centre_name})"
                Building.objects.create(
                    name=building_name, position=building_pos, population_centre=centre
                )
                placed_buildings.append((bx, by))
                self.stdout.write(f"  Placed {building_name} at {building_pos}")

        self.stdout.write(
            self.style.SUCCESS("Finished spawning population centres with buildings")
        )
