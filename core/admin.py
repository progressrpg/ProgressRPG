import re

from django import forms
from django.conf import settings
from django.contrib import admin
from django.utils import timezone

from .models import (
    Announcement,
    FeatureFlag,
    GameSettings,
    Image,
    PlayerAnnouncementState,
)

_FEATURE_FLAGS_TS = settings.BASE_DIR / "frontend" / "src" / "featureFlags.ts"
_FLAG_KEY_RE = re.compile(r"^\s{2}(\w+):\s*\[", re.MULTILINE)

_ACCESS_GROUP_CHOICES = [
    ("all", "All users"),
    ("premium", "Premium users"),
    ("testers", "Testers"),
]


def _load_flag_key_choices(exclude=()):
    try:
        text = _FEATURE_FLAGS_TS.read_text()
        keys = _FLAG_KEY_RE.findall(text)
    except FileNotFoundError:
        return []
    return [(k, k) for k in keys if k not in exclude]


class FeatureFlagForm(forms.ModelForm):
    access_groups = forms.MultipleChoiceField(
        choices=_ACCESS_GROUP_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    class Meta:
        model = FeatureFlag
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Exclude keys already assigned to another FeatureFlag row, so the
        # dropdown only offers keys that don't have one yet. When editing an
        # existing row, its own key stays selectable.
        already_used = set(
            FeatureFlag.objects.exclude(pk=self.instance.pk).values_list(
                "key", flat=True
            )
        )
        self.fields["key"] = forms.ChoiceField(
            choices=_load_flag_key_choices(exclude=already_used)
        )


@admin.register(FeatureFlag)
class FeatureFlagAdmin(admin.ModelAdmin):
    form = FeatureFlagForm
    list_display = ("key", "get_access_groups_display", "updated_at")
    search_fields = ("key", "description")

    @admin.display(description="Access groups")
    def get_access_groups_display(self, obj):
        return ", ".join(obj.access_groups) if obj.access_groups else "—"


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
    # Save individually (not queryset.update()) so Announcement.save()
    # broadcasts the "announcement_published" WebSocket event per row.
    for announcement in queryset:
        announcement.is_published = True
        announcement.published_at = now
        announcement.save()


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
