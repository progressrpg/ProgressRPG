# progression/admin.py

from django.contrib import admin
from django.contrib import admin
from .models import (
    Category,
    Role,
    PlayerSkill,
    CharacterSkill,
    PlayerActivity,
    CharacterActivity,
    CharacterQuest,
    Project,
    Task,
)


#########################################
#####      Group admins
#########################################


# @admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "player",
        "total_time",
        "total_records",
        "total_xp",
        "created_at",
    )
    search_fields = ("name", "description", "player__name")
    list_filter = ("player",)
    readonly_fields = ("total_time", "total_records", "total_xp")


# @admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "character",
        "total_time",
        "total_records",
        "total_xp",
        "created_at",
    )
    search_fields = ("name", "description", "character__name")
    list_filter = ("character",)
    readonly_fields = ("total_time", "total_records", "total_xp")


#########################################
#####      Skill admins
#########################################


# @admin.register(PlayerSkill)
class PlayerSkillAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "player",
        "category",
        "level",
        "is_private",
        "total_time",
        "total_records",
        "total_xp",
    )
    search_fields = ("name", "description", "player__name")
    list_filter = ("player", "is_private", "category")
    readonly_fields = ("total_time", "total_records", "total_xp")


# @admin.register(CharacterSkill)
class CharacterSkillAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "character",
        "level",
        "total_time",
        "total_records",
        "total_xp",
    )
    search_fields = ("name", "description", "character__name")
    list_filter = ("character", "roles")
    readonly_fields = ("total_time", "total_records", "total_xp")


#########################################
#####      TimeRecord admins
#########################################


@admin.register(PlayerActivity)
class PlayerActivityAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "player",
        "duration",
        "created_at",
        "started_at",
        "completed_at",
    )
    search_fields = ("name", "description", "player__name")
    list_filter = ("player", "is_private", "is_complete", "skill", "project", "task")
    date_hierarchy = "created_at"
    readonly_fields = ("created_at",)


@admin.register(CharacterActivity)
class CharacterActivityAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "kind",
        "character",
        "is_complete",
        "started_at",
        "completed_at",
        "scheduled_start",
        "scheduled_end",
    )
    search_fields = ("name", "description", "character__name")
    list_filter = ("created_at", "is_complete", "kind")
    date_hierarchy = "started_at"
    readonly_fields = ("created_at",)
    fields = (
        "character",
        ("name", "kind"),
        "duration",
        ("scheduled_start", "scheduled_end"),
        ("started_at", "completed_at"),
        "is_complete",
        "created_at",
    )


# @admin.register(CharacterQuest)
class CharacterQuestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "character",
        "skill",
        "duration",
        "target_duration",
        "is_complete",
        "created_at",
    )
    search_fields = ("name", "description", "character__name")
    list_filter = ("character", "is_complete", "stages_fixed")
    date_hierarchy = "created_at"


#########################################
#####      Other admins
#########################################


# @admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "player",
        "total_time",
        "total_records",
        "created_at",
        "is_complete",
        "completed_at",
    )
    search_fields = ("name", "description", "player__name")
    list_filter = ("player", "is_complete", "completed_at")
    readonly_fields = ("total_time", "total_records", "created_at", "completed_at")
    date_hierarchy = "created_at"


# @admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "player",
        "project",
        "total_time",
        "total_records",
        "created_at",
        "is_complete",
        "completed_at",
    )
    search_fields = ("name", "description", "player__name", "project__name")
    list_filter = ("player", "project", "is_complete", "completed_at")
    readonly_fields = ("total_time", "total_records", "created_at", "completed_at")
    date_hierarchy = "created_at"
