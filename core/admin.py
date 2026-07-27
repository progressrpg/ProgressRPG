from django.contrib import admin
from django.utils import timezone

from .models import Announcement, GameSettings, Image, PlayerAnnouncementState


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ("__str__", "alt_text", "created_at")
    search_fields = ("alt_text",)


@admin.register(GameSettings)
class GameSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "free_timer_limit_seconds",
        "daily_login_base_xp",
        "daily_login_max_xp",
        "premium_activity_xp_multiplier",
        "trial_period_days",
        "registration_cap",
        "registration_enabled",
        "self_serve_registration",
        "waitlist_signup_provider",
    )
    fieldsets = (
        ("Timer", {"fields": ("free_timer_limit_seconds",)}),
        (
            "Daily login XP",
            {
                "fields": (
                    "daily_login_base_xp",
                    "daily_login_streak_step_xp",
                    "daily_login_max_xp",
                )
            },
        ),
        (
            "Activity XP",
            {
                "fields": (
                    "default_activity_xp_per_second",
                    "task_activity_xp_multiplier",
                    "premium_activity_xp_multiplier",
                    "activity_search_includes_tasks",
                )
            },
        ),
        ("Stripe", {"fields": ("trial_period_days",)}),
        (
            "Registration",
            {
                "fields": (
                    "registration_cap",
                    "registration_enabled",
                    "self_serve_registration",
                    "waitlist_signup_provider",
                )
            },
        ),
    )

    def has_add_permission(self, request):
        return not GameSettings.objects.exists()


@admin.action(description="Publish selected announcements")
def publish_selected_announcements(_modeladmin, _request, queryset):
    now = timezone.now()
    queryset.update(is_published=True, published_at=now)


@admin.action(description="Unpublish selected announcements")
def unpublish_selected_announcements(_modeladmin, _request, queryset):
    queryset.update(is_published=False)


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "is_published",
        "published_at",
        "created_at",
        "updated_at",
    ]
    list_filter = ["is_published", "published_at", "created_at"]
    search_fields = ["title", "summary", "body"]
    actions = [publish_selected_announcements, unpublish_selected_announcements]


@admin.register(PlayerAnnouncementState)
class PlayerAnnouncementStateAdmin(admin.ModelAdmin):
    list_display = [
        "player",
        "announcement",
        "read_at",
        "created_at",
    ]
    list_filter = ["read_at", "created_at"]
    search_fields = ["player__name", "player__user__email", "announcement__title"]
    readonly_fields = ["created_at", "updated_at"]
