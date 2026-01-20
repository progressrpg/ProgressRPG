from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser, Profile, InviteCode
from character.models import PlayerCharacterLink, Character

# Register your models here.


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = [
        "email",
        "is_staff",
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
        ("Important dates", {"fields": ("last_login", "created_at")}),
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
    readonly_fields = ["created_at"]


@admin.register(Profile)
class PlayerAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "name",
        "get_character",
        "last_login",
        "user_created_at",
        "level",
    ]
    list_filter = [
        "last_login",
    ]

    fieldsets = (
        (None, {"fields": ("user", "name")}),
        (
            "Login",
            {
                "fields": (
                    "last_login",
                    "login_streak",
                    "login_streak_max",
                    "total_logins",
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

    readonly_fields = ["last_login", "user_created_at"]
    search_fields = ["name", "user__email"]
    ordering = ("-created_at",)

    @admin.display(description="Character")
    def get_character(self, obj):
        try:
            return PlayerCharacterLink.get_character(obj)
        except ValueError:
            return "-"

    @admin.display(boolean=True, description="Has Character")
    def has_character(self, obj):
        return PlayerCharacterLink.objects.filter(profile=obj, is_active=True).exists()

    @admin.display(
        description="User Created",
        ordering="user__created_at",
    )
    def user_created_at(self, obj):
        return obj.user.created_at


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
