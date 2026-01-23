# metrics/tests.py

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta, datetime

from users.models import Player
from progression.models import PlayerActivity
from .models import DailyEngagementSnapshot, UserEngagementMetrics, GlobalMetrics
from .services import MetricsCalculator
from .utils import track_user_session

User = get_user_model()


class BaseMetricsTestCase(TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(email="test@test.com", password="pass")
        self.player, _ = Player.objects.get_or_create(user=self.user)
        self.player.name = "Test Player"
        self.player.save()
        
        # Clear cache before each test
        cache.clear()

    def tearDown(self):
        """Clean up after tests."""
        cache.clear()


class SessionTrackingTests(BaseMetricsTestCase):
    def test_track_user_session_creates_snapshot(self):
        """Test that tracking a session creates a daily snapshot."""
        today = timezone.now().date()
        
        # Track session
        new_session = track_user_session(self.player)
        
        # Should be a new session
        self.assertTrue(new_session)
        
        # Should create a snapshot
        snapshot = DailyEngagementSnapshot.objects.get(player=self.player, date=today)
        self.assertEqual(snapshot.session_count, 1)

    def test_track_user_session_timeout(self):
        """Test that sessions timeout after 30 minutes."""
        cache_key = f"last_activity_{self.player.id}"
        now = timezone.now()
        
        # Set last activity to 31 minutes ago
        last_activity = now - timedelta(minutes=31)
        cache.set(cache_key, last_activity, 3600)
        
        # Track session - should be new session
        new_session = track_user_session(self.player)
        self.assertTrue(new_session)


class DailySnapshotTests(BaseMetricsTestCase):
    def test_calculate_daily_snapshot_no_activity(self):
        """Test calculating daily snapshot with no activities."""
        today = timezone.now().date()
        
        snapshot = MetricsCalculator.calculate_daily_snapshot(self.player, today)
        
        self.assertEqual(snapshot.player, self.player)
        self.assertEqual(snapshot.date, today)
        self.assertFalse(snapshot.had_activity)
        self.assertEqual(snapshot.activities_count, 0)
        self.assertEqual(snapshot.minutes_active, 0)

    def test_calculate_daily_snapshot_with_activity(self):
        """Test calculating daily snapshot with activities."""
        today = timezone.now().date()
        start_of_day = datetime.combine(today, datetime.min.time())
        start_of_day = timezone.make_aware(start_of_day)
        
        # Create a completed activity
        activity = PlayerActivity.objects.create(
            player=self.player,
            name="Test Activity",
            duration=3600,  # 60 minutes in seconds
            is_complete=True,
            completed_at=start_of_day + timedelta(hours=1)
        )
        
        snapshot = MetricsCalculator.calculate_daily_snapshot(self.player, today)
        
        self.assertTrue(snapshot.had_activity)
        self.assertEqual(snapshot.activities_count, 1)
        self.assertEqual(snapshot.minutes_active, 60)


class WeeklyMetricsTests(BaseMetricsTestCase):
    def test_calculate_weekly_metrics(self):
        """Test calculating weekly metrics."""
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        
        # Create daily snapshots for the week
        for i in range(3):
            date = week_start + timedelta(days=i)
            DailyEngagementSnapshot.objects.create(
                player=self.player,
                date=date,
                had_activity=True,
                session_count=2,
                activities_count=5,
                minutes_active=120
            )
        
        metrics = MetricsCalculator.calculate_weekly_metrics(self.player, week_start)
        
        self.assertEqual(metrics.player, self.player)
        self.assertEqual(metrics.week_start, week_start)
        self.assertEqual(metrics.active_days_count, 3)
        self.assertEqual(metrics.total_sessions, 6)
        self.assertEqual(metrics.activities_logged, 15)
        self.assertEqual(metrics.total_active_minutes, 360)


class GlobalMetricsTests(BaseMetricsTestCase):
    def test_calculate_global_metrics(self):
        """Test calculating global metrics."""
        today = timezone.now().date()
        
        # Create a daily snapshot
        DailyEngagementSnapshot.objects.create(
            player=self.player,
            date=today,
            had_activity=True,
            session_count=3,
            activities_count=10,
            minutes_active=200
        )
        
        metrics = MetricsCalculator.calculate_global_metrics(today)
        
        self.assertEqual(metrics.date, today)
        self.assertGreaterEqual(metrics.total_users, 1)
        self.assertEqual(metrics.active_users_today, 1)
        self.assertEqual(metrics.total_sessions_today, 3)
        self.assertEqual(metrics.total_activities_today, 10)
        self.assertEqual(metrics.total_minutes_today, 200)


class RetentionRateTests(BaseMetricsTestCase):
    def test_calculate_retention_rate(self):
        """Test retention rate calculation."""
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        prev_week_start = week_start - timedelta(days=7)
        
        # Create snapshots for previous week
        for i in range(2):
            date = prev_week_start + timedelta(days=i)
            DailyEngagementSnapshot.objects.create(
                player=self.player,
                date=date,
                had_activity=True,
                session_count=1,
                activities_count=1,
                minutes_active=60
            )
        
        # Create snapshots for current week (same player)
        for i in range(2):
            date = week_start + timedelta(days=i)
            DailyEngagementSnapshot.objects.create(
                player=self.player,
                date=date,
                had_activity=True,
                session_count=1,
                activities_count=1,
                minutes_active=60
            )
        
        retention_rate = MetricsCalculator.calculate_retention_rate(week_start)
        
        # Should be 100% since the same player was active both weeks
        self.assertEqual(retention_rate, 100.0)
