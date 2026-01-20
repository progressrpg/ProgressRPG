# gameplay/filters.py

import django_filters

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


class PlayerActivityFilter(django_filters.FilterSet):
    date = django_filters.DateFromToRangeFilter(field_name="completed_at")
    is_complete = django_filters.BooleanFilter(field_name="is_complete")
    created_at = django_filters.DateFromToRangeFilter(field_name="created_at")
    completed_at = django_filters.DateFromToRangeFilter(field_name="completed_at")

    class Meta:
        model = PlayerActivity
        fields = ["date", "is_complete", "created_at", "completed_at"]


class CharacterActivityFilter(django_filters.FilterSet):
    is_complete = django_filters.BooleanFilter(field_name="is_complete")
    completed_at = django_filters.DateFromToRangeFilter(field_name="completed_at")
    scheduled_start = django_filters.DateFromToRangeFilter(field_name="scheduled_start")
    scheduled_end = django_filters.DateFromToRangeFilter(field_name="scheduled_end")

    class Meta:
        model = CharacterActivity
        fields = ["is_complete", "completed_at", "scheduled_start", "scheduled_end"]


class PlayerSkillFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr="icontains")
    level = django_filters.RangeFilter(field_name="level")
    is_private = django_filters.BooleanFilter(field_name="is_private")
    category = django_filters.NumberFilter(field_name="category_id")
    created_at = django_filters.DateFromToRangeFilter(field_name="created_at")
    last_updated = django_filters.DateFromToRangeFilter(field_name="last_updated")

    class Meta:
        model = PlayerSkill
        fields = [
            "name",
            "level",
            "is_private",
            "category",
            "created_at",
            "last_updated",
        ]


class CategoryFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr="icontains")
    player = django_filters.NumberFilter(field_name="player_id")
    created_at = django_filters.DateFromToRangeFilter(field_name="created_at")
    last_updated = django_filters.DateFromToRangeFilter(field_name="last_updated")

    class Meta:
        model = Category
        fields = ["name", "player", "created_at", "last_updated"]


class ProjectFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr="icontains")
    player = django_filters.NumberFilter(field_name="player_id")
    created_at = django_filters.DateFromToRangeFilter(field_name="created_at")
    last_updated = django_filters.DateFromToRangeFilter(field_name="last_updated")

    class Meta:
        model = Project
        fields = [
            "name",
            "player",
            "created_at",
            "last_updated",
            "is_complete",
            "completed_at",
        ]


class TaskFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr="icontains")
    player = django_filters.NumberFilter(field_name="player_id")
    project = django_filters.NumberFilter(field_name="project_id")
    created_at = django_filters.DateFromToRangeFilter(field_name="created_at")
    last_updated = django_filters.DateFromToRangeFilter(field_name="last_updated")

    class Meta:
        model = Task
        fields = [
            "name",
            "player",
            "project",
            "created_at",
            "last_updated",
            "is_complete",
            "completed_at",
        ]
