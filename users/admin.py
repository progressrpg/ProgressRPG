from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser, UserLogin, Player, PlayerCurrency, InviteCode
from character.models import PlayerCharacterLink, Character

# Register your models here.


class PlayerInline(admin.TabularInline):
    model = Player
    extra = 0
    max_num = 1
    fields = [
        "name",
        "level",
        "is_online",
        "onboarding_step",
        "onboarding_completed",
    ]
    readonly_fields = fields


class UserLoginInline(admin.TabularInline):
    model = UserLogin
    extra = 0
    max_num = 10
    readonly_fields = ("timestamp", "is_first_login_of_day")
    can_delete = False


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = [
        "email",
        "is_staff",
        "get_player_online",
        "last_login",
        "created_at",
    ]
    list_filter = [
        "is_staff",
        # "get_player_online",
        "is_active",
    ]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ("date_of_birth",)}),
        ("Important dates", {"fields": ("created_at",)}),
        (
            "Logins",
            {
                "fields": (
                    (
                        "last_login",
                        "days_logged_in",
                        "current_login_streak",
                        "max_login_streak",
                    ),
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
        (
            "Billing",
            {
                "classes": ("collapse",),
                "fields": (
                    "stripe_customer_id",
                    "stripe_subscription_id",
                    "subscription_status",
                    "subscription_current_period_end",
                    "current_price_id",
                ),
            },
        ),
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
        "days_logged_in",
        "current_login_streak",
        "max_login_streak",
    ]
    inlines = [PlayerInline, UserLoginInline]

    def last_login(self, obj):
        return obj.last_login

    def days_logged_in(self, obj):
        return obj.days_logged_in

    def current_login_streak(self, obj):
        return obj.current_login_streak

    def max_login_streak(self, obj):
        return obj.max_login_streak

    @admin.display(boolean=True, description="Player online")
    def get_player_online(self, obj):
        try:
            return obj.player.is_online
        except Player.DoesNotExist:
            return


class CurrencyInline(admin.TabularInline):
    model = PlayerCurrency
    extra = 0


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "level",
        "user",
        "is_online",
        "get_character",
        "user_created_at",
    ]

    fieldsets = (
        (
            None,
            {
                "fields": (
                    ("name", "is_online"),
                    "user",
                )
            },
        ),
        (
            "Levels/xp",
            {
                #'classes': ('collapse',),
                "fields": (
                    ("xp", "xp_next_level", "xp_modifier"),
                    "level",
                ),
            },
        ),
        (
            "Metrics",
            {
                "fields": (("total_time", "total_activities"),),
            },
        ),
        (
            "Other",
            {
                "fields": (
                    (
                        "is_premium",
                        "onboarding_completed",
                        "onboarding_step",
                    ),
                ),
            },
        ),
    )

    readonly_fields = [
        "user_created_at",
        "total_time",
        "total_activities",
        "is_premium",
        "is_online",
    ]
    search_fields = ["name", "user__email"]
    ordering = ("-created_at",)
    inlines = [CurrencyInline]

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

    def is_premium(self, obj):
        return obj.is_premium


@admin.register(PlayerCurrency)
class PlayerCurrencyAdmin(admin.ModelAdmin):
    list_display = ["player", "name", "balance"]
    list_filter = ["name"]
    search_fields = ["player__name", "player__user__email"]
    readonly_fields = ["player", "name"]
    fieldsets = (
        (None, {"fields": ("player", "name")}),
        ("Amounts", {"fields": ("balance", "earned", "spent")}),
    )

    def balance(self, obj):
        return obj.balance


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
