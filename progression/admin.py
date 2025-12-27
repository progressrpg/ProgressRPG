from django.contrib import admin

from .models import Activity, CharacterQuest

# progression/admin.py
from django.contrib import admin
from .models import (
    Category,
    Role,
    PlayerSkill,
    CharacterSkill,
    Activity,
    CharacterQuest,
    Project,
    Task,
)


#########################################
#####      Group admins
#########################################


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "profile",
        "total_time",
        "total_records",
        "total_xp",
        "created_at",
    )
    search_fields = ("name", "description", "profile__name")
    list_filter = ("profile",)
    readonly_fields = ("total_time", "total_records", "total_xp")


@admin.register(Role)
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


@admin.register(PlayerSkill)
class PlayerSkillAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "profile",
        "category",
        "level",
        "is_private",
        "total_time",
        "total_records",
        "total_xp",
    )
    search_fields = ("name", "description", "profile__name")
    list_filter = ("profile", "is_private", "category")
    readonly_fields = ("total_time", "total_records", "total_xp")


@admin.register(CharacterSkill)
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


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "profile",
        "skill",
        "project",
        "task",
        "duration",
        "is_private",
        "is_complete",
        "created_at",
    )
    search_fields = ("name", "description", "profile__name")
    list_filter = ("profile", "is_private", "is_complete", "skill", "project", "task")
    date_hierarchy = "created_at"

    class Meta:
        verbose_name = "Activity"  # singular name
        verbose_name_plural = "Activities"  # plural name


@admin.register(CharacterQuest)
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


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "profile",
        "total_time",
        "total_records",
        "created_at",
        "is_complete",
        "completed_at",
    )
    search_fields = ("name", "description", "profile__name")
    list_filter = ("profile", "is_complete", "completed_at")
    readonly_fields = ("total_time", "total_records", "created_at", "completed_at")
    date_hierarchy = "created_at"


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "profile",
        "project",
        "total_time",
        "total_records",
        "created_at",
        "is_complete",
        "completed_at",
    )
    search_fields = ("name", "description", "profile__name", "project__name")
    list_filter = ("profile", "project", "is_complete", "completed_at")
    readonly_fields = ("total_time", "total_records", "created_at", "completed_at")
    date_hierarchy = "created_at"
