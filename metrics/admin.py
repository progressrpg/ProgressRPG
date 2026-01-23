# metrics/admin.py

from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.db.models import Avg, Sum
from django.utils import timezone
from datetime import timedelta
from .models import DailyEngagementSnapshot, UserEngagementMetrics, GlobalMetrics
from .services import MetricsCalculator


@admin.register(GlobalMetrics)
class GlobalMetricsAdmin(admin.ModelAdmin):
    list_display = [
        "date",
        "total_users",
        "active_users_today",
        "new_users_today",
        "total_activities_today",
        "total_minutes_today",
        "week_over_week_retention_display",
    ]
    list_filter = ["date"]
    readonly_fields = [
        "date",
        "total_users",
        "active_users_today",
        "new_users_today",
        "total_sessions_today",
        "total_activities_today",
        "total_minutes_today",
        "week_over_week_retention",
        "created_at",
    ]

    def week_over_week_retention_display(self, obj):
        """Display retention as percentage with % sign."""
        if obj.week_over_week_retention is not None:
            return f"{obj.week_over_week_retention:.2f}%"
        return "-"

    week_over_week_retention_display.short_description = "Week/Week Retention"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("dashboard/", self.admin_site.admin_view(self.dashboard_view), name="metrics_dashboard"),
        ]
        return custom_urls + urls

    def dashboard_view(self, request):
        """Custom dashboard view for metrics."""
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        # Get latest global metrics
        latest_global = GlobalMetrics.objects.first()

        # Calculate current week averages
        current_week_metrics = UserEngagementMetrics.objects.filter(
            week_start=week_start
        ).aggregate(
            avg_active_days=Avg("active_days_count"),
            avg_sessions=Avg("total_sessions"),
            avg_activities=Avg("activities_logged"),
            avg_minutes=Avg("total_active_minutes"),
        )

        # Calculate retention rate for current week
        retention_rate = MetricsCalculator.calculate_retention_rate(week_start)

        # Get last 7 days of global metrics
        recent_metrics = GlobalMetrics.objects.all()[:7]

        context = {
            **self.admin_site.each_context(request),
            "title": "Metrics Dashboard",
            "latest_global": latest_global,
            "current_week": {
                "avg_active_days": current_week_metrics["avg_active_days"] or 0,
                "avg_sessions": current_week_metrics["avg_sessions"] or 0,
                "avg_activities": current_week_metrics["avg_activities"] or 0,
                "avg_minutes": current_week_metrics["avg_minutes"] or 0,
                "retention_rate": retention_rate or 0,
            },
            "recent_metrics": recent_metrics,
        }

        return render(request, "admin/metrics_dashboard.html", context)


@admin.register(UserEngagementMetrics)
class UserEngagementMetricsAdmin(admin.ModelAdmin):
    list_display = [
        "player",
        "week_start",
        "active_days_count",
        "total_sessions",
        "activities_logged",
        "total_active_minutes",
        "retained_from_previous_week",
    ]
    list_filter = ["week_start", "retained_from_previous_week"]
    search_fields = ["player__name", "player__user__email"]
    readonly_fields = [
        "player",
        "week_start",
        "week_end",
        "active_days_count",
        "total_sessions",
        "activities_logged",
        "total_active_minutes",
        "retained_from_previous_week",
        "created_at",
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DailyEngagementSnapshot)
class DailyEngagementSnapshotAdmin(admin.ModelAdmin):
    list_display = [
        "player",
        "date",
        "had_activity",
        "activities_count",
        "minutes_active",
    ]
    list_filter = ["date", "had_activity"]
    search_fields = ["player__name"]
    readonly_fields = [
        "player",
        "date",
        "had_activity",
        "session_count",
        "activities_count",
        "minutes_active",
        "created_at",
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
