# metrics/models.py

from django.db import models
from django.utils import timezone


class DailyEngagementSnapshot(models.Model):
    """Track daily activity per user."""

    player = models.ForeignKey(
        "users.Player", on_delete=models.CASCADE, related_name="daily_snapshots"
    )
    date = models.DateField()
    had_activity = models.BooleanField(default=False)
    session_count = models.PositiveIntegerField(default=0)
    activities_count = models.PositiveIntegerField(default=0)
    minutes_active = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [["player", "date"]]
        indexes = [
            models.Index(fields=["date"]),
            models.Index(fields=["player", "date"]),
        ]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.player.name} - {self.date}"


class UserEngagementMetrics(models.Model):
    """Track weekly aggregated metrics per user."""

    player = models.ForeignKey(
        "users.Player", on_delete=models.CASCADE, related_name="weekly_metrics"
    )
    week_start = models.DateField()
    week_end = models.DateField()
    active_days_count = models.PositiveIntegerField(default=0)
    total_sessions = models.PositiveIntegerField(default=0)
    activities_logged = models.PositiveIntegerField(default=0)
    total_active_minutes = models.PositiveIntegerField(default=0)
    retained_from_previous_week = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [["player", "week_start"]]
        indexes = [
            models.Index(fields=["week_start"]),
            models.Index(fields=["player", "week_start"]),
        ]
        ordering = ["-week_start"]

    def __str__(self):
        return f"{self.player.name} - Week of {self.week_start}"


class GlobalMetrics(models.Model):
    """Track platform-wide daily metrics."""

    date = models.DateField(unique=True)
    total_users = models.PositiveIntegerField(default=0)
    active_users_today = models.PositiveIntegerField(default=0)
    new_users_today = models.PositiveIntegerField(default=0)
    total_sessions_today = models.PositiveIntegerField(default=0)
    total_activities_today = models.PositiveIntegerField(default=0)
    total_minutes_today = models.PositiveIntegerField(default=0)
    week_over_week_retention = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]
        verbose_name_plural = "Global Metrics"

    def __str__(self):
        return f"Global metrics for {self.date}"
