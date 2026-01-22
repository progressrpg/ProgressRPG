# metrics/tasks.py

from celery import shared_task
from django.utils import timezone
from users.models import Player
from .services import MetricsCalculator
import logging

logger = logging.getLogger("general")


@shared_task
def calculate_daily_metrics():
    """
    Celery task to calculate daily metrics.
    Runs daily (suggested: 1 AM).
    """
    today = timezone.now().date()
    logger.info(f"Starting daily metrics calculation for {today}")

    # Get all non-deleted players
    players = Player.objects.filter(is_deleted=False)
    player_count = players.count()

    # Calculate daily snapshots for all players
    for player in players:
        MetricsCalculator.calculate_daily_snapshot(player, today)

    # Calculate global metrics for today
    MetricsCalculator.calculate_global_metrics(today)

    summary = (
        f"Daily metrics calculated for {today}: "
        f"{player_count} players processed"
    )
    logger.info(summary)
    return summary


@shared_task
def calculate_weekly_metrics():
    """
    Celery task to calculate weekly metrics.
    Runs on Mondays (suggested: 2 AM).
    """
    today = timezone.now().date()
    logger.info(f"Starting weekly metrics calculation for week of {today}")

    # Get all non-deleted players
    players = Player.objects.filter(is_deleted=False)
    player_count = players.count()

    # Calculate weekly metrics for all players
    for player in players:
        MetricsCalculator.calculate_weekly_metrics(player, today)

    summary = (
        f"Weekly metrics calculated for week of {today}: "
        f"{player_count} players processed"
    )
    logger.info(summary)
    return summary
