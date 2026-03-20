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
    Uses iterator() to process players in batches.
    """
    today = timezone.now().date()
    logger.info(f"Starting daily metrics calculation for {today}")

    player_count = 0
    batch_size = 100

    # Calculate daily snapshots for all non-deleted players using iterator() for memory efficiency
    for player in (
        Player.objects.filter(is_deleted=False)
        .only("id")
        .iterator(chunk_size=batch_size)
    ):
        MetricsCalculator.calculate_daily_snapshot(player, today)
        player_count += 1

    # Calculate global metrics for today
    MetricsCalculator.calculate_global_metrics(today)

    summary = (
        f"Daily metrics calculated for {today}: " f"{player_count} players processed"
    )
    logger.info(summary)
    return summary


@shared_task
def calculate_weekly_metrics():
    """
    Celery task to calculate weekly metrics.
    Runs on Mondays (suggested: 2 AM).
    Uses iterator() to process players in batches.
    """
    today = timezone.now().date()
    logger.info(f"Starting weekly metrics calculation for week of {today}")

    player_count = 0
    batch_size = 100

    # Calculate weekly metrics for all non-deleted players using iterator() for memory efficiency
    for player in (
        Player.objects.filter(is_deleted=False)
        .only("id")
        .iterator(chunk_size=batch_size)
    ):
        MetricsCalculator.calculate_weekly_metrics(player, today)
        player_count += 1

    summary = (
        f"Weekly metrics calculated for week of {today}: "
        f"{player_count} players processed"
    )
    logger.info(summary)
    return summary
