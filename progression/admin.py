from django.contrib import admin

from .models import Activity, CharacterQuest


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ["profile", "name", "duration", "created_at"]
    list_filter = [
        "created_at",
        "duration",
    ]
    fields = [
        "name",
        "profile",
        "description",
        "duration",
        ("created_at", "last_updated", "completed_at"),
    ]
    readonly_fields = ["created_at", "last_updated", "completed_at"]
    date_hierarchy = "created_at"
    show_full_result_count = False


@admin.register(CharacterQuest)
class CharacterQuestAdmin(admin.ModelAdmin):
    list_display = ["character", "name", "duration", "created_at"]
    list_filter = [
        "created_at",
        "duration",
    ]
    fields = [
        "name",
        "character",
        "description",
        "duration",
        ("created_at", "last_updated", "completed_at"),
    ]
    readonly_fields = ["created_at", "last_updated", "completed_at"]
    date_hierarchy = "created_at"
    show_full_result_count = False
