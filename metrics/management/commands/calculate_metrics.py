# metrics/management/commands/calculate_metrics.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, datetime
from users.models import Player
from metrics.services import MetricsCalculator


class Command(BaseCommand):
    help = "Calculate engagement metrics for players"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help="Number of days to calculate metrics for (default: 7)",
        )
        parser.add_argument(
            "--date",
            type=str,
            help="Specific date to calculate in YYYY-MM-DD format",
        )

    def handle(self, *args, **options):
        days = options["days"]
        specific_date = options.get("date")

        if specific_date:
            # Parse the specific date
            try:
                target_date = datetime.strptime(specific_date, "%Y-%m-%d").date()
                dates_to_process = [target_date]
                self.stdout.write(f"Calculating metrics for {specific_date}")
            except ValueError:
                self.stdout.write(
                    self.style.ERROR(
                        f"Invalid date format: {specific_date}. Use YYYY-MM-DD"
                    )
                )
                return
        else:
            # Calculate for the last N days
            today = timezone.now().date()
            dates_to_process = [today - timedelta(days=i) for i in range(days)]
            dates_to_process.reverse()  # Process oldest first
            self.stdout.write(f"Calculating metrics for the last {days} days")

        # Get all non-deleted players
        players = Player.objects.filter(is_deleted=False)
        player_count = players.count()
        self.stdout.write(f"Processing {player_count} players")

        # Process each date
        for target_date in dates_to_process:
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(f"Processing date: {target_date}")
            self.stdout.write(f"{'='*60}")

            # Calculate daily snapshots for all players
            for index, player in enumerate(players, 1):
                if index % 10 == 0:
                    self.stdout.write(
                        f"  Progress: {index}/{player_count} players processed"
                    )
                MetricsCalculator.calculate_daily_snapshot(player, target_date)

            # Calculate global metrics for the date
            MetricsCalculator.calculate_global_metrics(target_date)
            self.stdout.write(
                self.style.SUCCESS(f"✓ Completed daily metrics for {target_date}")
            )

            # If it's a Monday or the last day, calculate weekly metrics
            if target_date.weekday() == 0 or target_date == dates_to_process[-1]:
                self.stdout.write(f"\nCalculating weekly metrics...")
                for player in players:
                    MetricsCalculator.calculate_weekly_metrics(player, target_date)
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Completed weekly metrics for week of {target_date}")
                )

        self.stdout.write("\n" + "="*60)
        self.stdout.write(
            self.style.SUCCESS(
                f"✓ All metrics calculated successfully for {len(dates_to_process)} day(s)"
            )
        )
