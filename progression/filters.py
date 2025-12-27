# gameplay/filters.py

import django_filters

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


class ActivityFilter(django_filters.FilterSet):
    date = django_filters.DateFromToRangeFilter(field_name="completed_at")
    is_complete = django_filters.BooleanFilter(field_name="is_complete")
    skill = django_filters.NumberFilter(field_name="skill_id")
    created_at = django_filters.DateFromToRangeFilter(field_name="created_at")

    class Meta:
        model = Activity
        fields = ["date", "is_complete", "created_at", "skill"]


from progression.models import PlayerSkill, Category


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
    profile = django_filters.NumberFilter(field_name="profile_id")
    created_at = django_filters.DateFromToRangeFilter(field_name="created_at")
    last_updated = django_filters.DateFromToRangeFilter(field_name="last_updated")

    class Meta:
        model = Category
        fields = ["name", "profile", "created_at", "last_updated"]


class ProjectFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr="icontains")
    profile = django_filters.NumberFilter(field_name="profile_id")
    created_at = django_filters.DateFromToRangeFilter(field_name="created_at")
    last_updated = django_filters.DateFromToRangeFilter(field_name="last_updated")

    class Meta:
        model = Project
        fields = [
            "name",
            "profile",
            "created_at",
            "last_updated",
            "is_complete",
            "completed_at",
        ]


class TaskFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr="icontains")
    profile = django_filters.NumberFilter(field_name="profile_id")
    project = django_filters.NumberFilter(field_name="project_id")
    created_at = django_filters.DateFromToRangeFilter(field_name="created_at")
    last_updated = django_filters.DateFromToRangeFilter(field_name="last_updated")

    class Meta:
        model = Task
        fields = [
            "name",
            "profile",
            "project",
            "created_at",
            "last_updated",
            "is_complete",
            "completed_at",
        ]
