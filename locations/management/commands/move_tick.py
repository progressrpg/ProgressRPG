from django.core.management.base import BaseCommand
from character.models import Character


class Command(BaseCommand):
    help = "Move all Movable objects toward their target_location"

    def add_arguments(self, parser):
        parser.add_argument(
            "--ticks", type=int, default=1, help="Number of movement ticks to simulate"
        )
        parser.add_argument(
            "--time-delta",
            type=float,
            default=1.0,
            help="Time delta per tick for movement calculation",
        )

    def handle(self, *args, **options):
        ticks = options["ticks"]
        time_delta = options["time_delta"]

        # Assuming Character inherits from Movable
        movables = Character.objects.filter(target_location__isnull=False)
        if not movables.exists():
            self.stdout.write(self.style.WARNING("No characters with target_location"))
            return

        for tick in range(1, ticks + 1):
            self.stdout.write(f"Tick {tick}:")
            for obj in movables:
                still_moving, distance_travelled = obj.step_toward(
                    time_delta=time_delta
                )
                self.stdout.write(
                    f"  {obj.name} at {obj.location.x:.2f}, {obj.location.y:.2f}. Travelled {distance_travelled}m."
                )
                if not still_moving:
                    self.stdout.write(f"    {obj.name} arrived at target")
