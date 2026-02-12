from django.core.management.base import BaseCommand
from gameworld.models import GameWorld
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = "Test GameWorld sun phases for today or a range of hours"

    def add_arguments(self, parser):
        parser.add_argument(
            "--hours",
            type=int,
            default=24,
            help="Number of hours to simulate starting from midnight",
        )

    def handle(self, *args, **options):
        world = GameWorld.get_instance()
        hours = options["hours"]

        today = (
            datetime.now()
            .astimezone()
            .replace(hour=0, minute=0, second=0, microsecond=0)
        )

        self.stdout.write(f"Sun phases for {today.date()} in world '{world.name}':\n")
        for h in range(hours):
            current_time = today + timedelta(hours=h)
            phase = world.current_sun_phase(current_time)
            self.stdout.write(f"{current_time.strftime('%H:%M')}: {phase}")
