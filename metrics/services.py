# metrics/services.py

from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta, date, datetime
import logging

from users.models import Player
from progression.models import PlayerActivity
from .models import DailyEngagementSnapshot, UserEngagementMetrics, GlobalMetrics

logger = logging.getLogger("general")

SESSION_TIMEOUT = 1800  # 30 minutes in seconds


class MetricsCalculator:
    """Service class for calculating engagement metrics."""

    @staticmethod
    def calculate_sessions_from_activities(player, target_date):
        """
        Calculate sessions by detecting gaps >30 minutes between activities.
        
        Args:
            player: The Player object
            target_date: The date to calculate sessions for
        
        Returns:
            int: Number of sessions detected
        """
        # Get all completed activities for the target date, ordered by created_at
        start_of_day = datetime.combine(target_date, datetime.min.time())
        end_of_day = datetime.combine(target_date, datetime.max.time())
        
        # Make them timezone-aware
        start_of_day = timezone.make_aware(start_of_day)
        end_of_day = timezone.make_aware(end_of_day)
        
        activities = PlayerActivity.objects.filter(
            player=player,
            is_complete=True,
            completed_at__gte=start_of_day,
            completed_at__lte=end_of_day,
        ).order_by('completed_at').values_list('completed_at', flat=True)
        
        if not activities:
            return 0
        
        # Count sessions by detecting gaps
        sessions = 1  # At least one session if there are activities
        prev_time = None
        
        for activity_time in activities:
            if prev_time is not None:
                gap = (activity_time - prev_time).total_seconds()
                if gap > SESSION_TIMEOUT:
                    sessions += 1
            prev_time = activity_time
        
        return sessions

    @staticmethod
    def calculate_daily_snapshot(player, target_date=None):
        """
        Calculate metrics for a single player for a given date.
        
        Args:
            player: The Player object
            target_date: The date to calculate (defaults to today)
        
        Returns:
            DailyEngagementSnapshot: The created or updated snapshot
        """
        if target_date is None:
            target_date = timezone.now().date()
        
        # Get start and end of day as timezone-aware datetimes
        start_of_day = datetime.combine(target_date, datetime.min.time())
        end_of_day = datetime.combine(target_date, datetime.max.time())
        start_of_day = timezone.make_aware(start_of_day)
        end_of_day = timezone.make_aware(end_of_day)
        
        # Query PlayerActivity objects for the date range
        activities = PlayerActivity.objects.filter(
            player=player,
            is_complete=True,
            completed_at__gte=start_of_day,
            completed_at__lte=end_of_day,
        )
        
        # Count completed activities
        activities_count = activities.count()
        
        # Sum duration and convert to minutes
        total_seconds = activities.aggregate(total=Sum('duration'))['total'] or 0
        minutes_active = total_seconds // 60
        
        # Calculate sessions
        sessions = MetricsCalculator.calculate_sessions_from_activities(
            player, target_date
        )
        
        # Determine if there was any activity
        had_activity = activities_count > 0
        
        # Create or update DailyEngagementSnapshot
        snapshot, created = DailyEngagementSnapshot.objects.update_or_create(
            player=player,
            date=target_date,
            defaults={
                'had_activity': had_activity,
                'session_count': sessions,
                'activities_count': activities_count,
                'minutes_active': minutes_active,
            }
        )
        
        logger.info(
            f"Daily snapshot {'created' if created else 'updated'} for "
            f"player {player.id} on {target_date}: {activities_count} activities, "
            f"{sessions} sessions, {minutes_active} minutes"
        )
        
        return snapshot

    @staticmethod
    def calculate_weekly_metrics(player, week_start=None):
        """
        Calculate weekly aggregate for a player.
        
        Args:
            player: The Player object
            week_start: The Monday of the target week (defaults to current week)
        
        Returns:
            UserEngagementMetrics: The created or updated weekly metrics
        """
        if week_start is None:
            # Get Monday of current week
            today = timezone.now().date()
            week_start = today - timedelta(days=today.weekday())
        
        # Ensure week_start is a Monday
        if week_start.weekday() != 0:
            week_start = week_start - timedelta(days=week_start.weekday())
        
        week_end = week_start + timedelta(days=6)
        
        # Query DailyEngagementSnapshot for the week (7 days)
        snapshots = DailyEngagementSnapshot.objects.filter(
            player=player,
            date__gte=week_start,
            date__lte=week_end,
        )
        
        # Aggregate metrics
        active_days = snapshots.filter(had_activity=True).count()
        total_sessions = snapshots.aggregate(total=Sum('session_count'))['total'] or 0
        activities_logged = snapshots.aggregate(total=Sum('activities_count'))['total'] or 0
        total_minutes = snapshots.aggregate(total=Sum('minutes_active'))['total'] or 0
        
        # Check retention: did player have activity in previous week AND current week?
        prev_week_start = week_start - timedelta(days=7)
        prev_week_end = prev_week_start + timedelta(days=6)
        
        had_activity_prev_week = DailyEngagementSnapshot.objects.filter(
            player=player,
            date__gte=prev_week_start,
            date__lte=prev_week_end,
            had_activity=True,
        ).exists()
        
        had_activity_curr_week = snapshots.filter(had_activity=True).exists()
        
        retained = had_activity_prev_week and had_activity_curr_week
        
        # Create or update UserEngagementMetrics
        metrics, created = UserEngagementMetrics.objects.update_or_create(
            player=player,
            week_start=week_start,
            defaults={
                'week_end': week_end,
                'active_days_count': active_days,
                'total_sessions': total_sessions,
                'activities_logged': activities_logged,
                'total_active_minutes': total_minutes,
                'retained_from_previous_week': retained,
            }
        )
        
        logger.info(
            f"Weekly metrics {'created' if created else 'updated'} for "
            f"player {player.id} week of {week_start}: {active_days} active days, "
            f"{total_sessions} sessions, {activities_logged} activities"
        )
        
        return metrics

    @staticmethod
    def calculate_retention_rate(week_start):
        """
        Calculate week-over-week retention rate.
        
        Args:
            week_start: The Monday of the target week
        
        Returns:
            float: Retention rate as percentage (0-100), or None if no data
        """
        week_end = week_start + timedelta(days=6)
        prev_week_start = week_start - timedelta(days=7)
        prev_week_end = prev_week_start + timedelta(days=6)
        
        # Get users active in previous week
        prev_week_users = set(
            DailyEngagementSnapshot.objects.filter(
                date__gte=prev_week_start,
                date__lte=prev_week_end,
                had_activity=True,
            ).values_list('player_id', flat=True).distinct()
        )
        
        if not prev_week_users:
            return None
        
        # Get users active in current week
        curr_week_users = set(
            DailyEngagementSnapshot.objects.filter(
                date__gte=week_start,
                date__lte=week_end,
                had_activity=True,
            ).values_list('player_id', flat=True).distinct()
        )
        
        # Calculate retention: users active in both weeks
        retained_users = prev_week_users.intersection(curr_week_users)
        
        # Calculate percentage
        retention_rate = (len(retained_users) / len(prev_week_users)) * 100
        
        return round(retention_rate, 2)

    @staticmethod
    def calculate_global_metrics(target_date=None):
        """
        Calculate platform-wide metrics for a date.
        
        Args:
            target_date: The date to calculate (defaults to today)
        
        Returns:
            GlobalMetrics: The created or updated global metrics
        """
        if target_date is None:
            target_date = timezone.now().date()
        
        # Count total non-deleted players
        total_users = Player.objects.filter(is_deleted=False).count()
        
        # Count new players created on the date
        start_of_day = datetime.combine(target_date, datetime.min.time())
        end_of_day = datetime.combine(target_date, datetime.max.time())
        start_of_day = timezone.make_aware(start_of_day)
        end_of_day = timezone.make_aware(end_of_day)
        
        new_users = Player.objects.filter(
            created_at__gte=start_of_day,
            created_at__lte=end_of_day,
            is_deleted=False,
        ).count()
        
        # Count active users from DailyEngagementSnapshot
        active_users = DailyEngagementSnapshot.objects.filter(
            date=target_date,
            had_activity=True,
        ).count()
        
        # Aggregate daily snapshots for totals
        daily_aggregates = DailyEngagementSnapshot.objects.filter(
            date=target_date
        ).aggregate(
            total_sessions=Sum('session_count'),
            total_activities=Sum('activities_count'),
            total_minutes=Sum('minutes_active'),
        )
        
        total_sessions = daily_aggregates['total_sessions'] or 0
        total_activities = daily_aggregates['total_activities'] or 0
        total_minutes = daily_aggregates['total_minutes'] or 0
        
        # Calculate retention rate for the week containing this date
        # Find the Monday of the week containing target_date
        week_start = target_date - timedelta(days=target_date.weekday())
        retention_rate = MetricsCalculator.calculate_retention_rate(week_start)
        
        # Create or update GlobalMetrics
        metrics, created = GlobalMetrics.objects.update_or_create(
            date=target_date,
            defaults={
                'total_users': total_users,
                'active_users_today': active_users,
                'new_users_today': new_users,
                'total_sessions_today': total_sessions,
                'total_activities_today': total_activities,
                'total_minutes_today': total_minutes,
                'week_over_week_retention': retention_rate,
            }
        )
        
        logger.info(
            f"Global metrics {'created' if created else 'updated'} for {target_date}: "
            f"{active_users} active users, {new_users} new users, "
            f"{total_activities} activities"
        )
        
        return metrics
