from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser, Player, PlayerCurrency, UserLogin, InviteCode
from character.models import PlayerCharacterLink, Character

# Register your models here.


class PlayerInline(admin.TabularInline):
    model = Player
    extra = 0
    max_num = 1


class UserLoginInline(admin.TabularInline):
    model = UserLogin
    extra = 0
    max_num = 10
    readonly_fields = ("timestamp", "is_first_login_of_day")
    can_delete = False


class PlayerCurrencyInline(admin.TabularInline):
    model = PlayerCurrency
    extra = 0
    fields = ("currency", "earned", "spent", "balance", "last_calculated_at")
    readonly_fields = ("balance",)


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = [
        "email",
        "is_staff",
        "get_player_online",
        "last_recorded_login",
        "is_active",
        "created_at",
    ]
    list_filter = [
        "is_staff",
        "is_active",
    ]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ("date_of_birth",)}),
        (
            "Logins",
            {
                "fields": (
                    "last_login",
                    "last_recorded_login",
                    "days_logged_in",
                    "current_login_streak",
                    "max_login_streak",
                )
            },
        ),
        (
            "Permissions",
            {
                "classes": ("collapse",),
                "fields": (
                    "is_staff",
                    "is_superuser",
                    "is_active",
                    "is_confirmed",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        ("Important dates", {"fields": ("created_at",)}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "is_staff", "is_active"),
            },
        ),
    )
    search_fields = ["email"]
    ordering = ("-created_at",)
    readonly_fields = [
        "created_at",
        "last_login",
        "last_recorded_login",
        "days_logged_in",
        "current_login_streak",
        "max_login_streak",
    ]
    inlines = [PlayerInline, UserLoginInline]

    @admin.display(description="Recorded login")
    def last_recorded_login(self, obj):
        return obj.last_recorded_login

    @admin.display(description="Days logged in")
    def days_logged_in(self, obj):
        return obj.days_logged_in

    @admin.display(description="Current streak")
    def current_login_streak(self, obj):
        return obj.current_login_streak

    @admin.display(description="Max streak")
    def max_login_streak(self, obj):
        return obj.max_login_streak

    @admin.display(boolean=True, description="Player online")
    def get_player_online(self, obj):
        try:
            return obj.player.is_online
        except Player.DoesNotExist:
            return None


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "name",
        "get_character",
        "current_login_streak",
        "days_logged_in",
        "user_created_at",
        "level",
    ]
    list_filter = [
        "last_seen",
    ]

    fieldsets = (
        (None, {"fields": ("user", "name")}),
        (
            "Presence",
            {
                "fields": (
                    "is_online",
                    "active_connections",
                    "last_seen",
                ),
            },
        ),
        (
            "Login",
            {
                "fields": (
                    "days_logged_in",
                    "current_login_streak",
                    "max_login_streak",
                ),
            },
        ),
        (
            "Levels/xp",
            {
                #'classes': ('collapse',),
                "fields": (
                    "xp",
                    "xp_next_level",
                    "xp_modifier",
                    "level",
                ),
            },
        ),
        (
            "Metrics",
            {
                "fields": ("total_time", "total_activities"),
            },
        ),
        (
            "Other",
            {
                "fields": ("onboarding_completed", "is_premium"),
            },
        ),
    )

    readonly_fields = [
        "is_online",
        "active_connections",
        "last_seen",
        "days_logged_in",
        "current_login_streak",
        "max_login_streak",
        "user_created_at",
        "total_time",
        "total_activities",
    ]
    search_fields = ["name", "user__email"]
    ordering = ("-created_at",)
    inlines = [PlayerCurrencyInline]

    @admin.display(description="Character")
    def get_character(self, obj):
        try:
            return PlayerCharacterLink.get_character(obj)
        except ValueError:
            return "-"

    @admin.display(boolean=True, description="Has Character")
    def has_character(self, obj):
        return PlayerCharacterLink.objects.filter(player=obj, is_active=True).exists()

    @admin.display(
        description="User Created",
        ordering="user__created_at",
    )
    def user_created_at(self, obj):
        return obj.user.created_at

    @admin.display(description="Days logged in")
    def days_logged_in(self, obj):
        return obj.user.days_logged_in

    @admin.display(description="Current streak")
    def current_login_streak(self, obj):
        return obj.user.current_login_streak

    @admin.display(description="Max streak")
    def max_login_streak(self, obj):
        return obj.user.max_login_streak


@admin.register(InviteCode)
class InviteCodeAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "is_active",
        "max_uses",
        "uses",
        "expires_at",
    ]
    list_filter = [
        "is_active",
    ]
    fields = [
        "code",
        "is_active",
        "expires_at",
        "max_uses",
        "uses",
    ]
    readonly_fields = ["uses"]


@admin.register(PlayerCurrency)
class PlayerCurrencyAdmin(admin.ModelAdmin):
    list_display = ["player", "currency", "balance", "earned", "spent"]
    list_filter = ["currency"]
    search_fields = [
        "player__name",
        "player__user__email",
        "currency__code",
        "currency__name",
    ]
    readonly_fields = ["balance"]
