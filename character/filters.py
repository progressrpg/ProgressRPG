# gameplay/filters.py
import django_filters
from .models import Character


class CharacterFilter(django_filters.FilterSet):
    level = django_filters.RangeFilter(field_name="level")
    xp = django_filters.RangeFilter(field_name="xp")
    is_npc = django_filters.BooleanFilter(method="filter_is_npc")
    can_link = django_filters.BooleanFilter(field_name="can_link")

    class Meta:
        model = Character
        fields = ["level", "xp", "is_npc", "can_link"]

    def filter_is_npc(self, queryset, name, value):
        """Filter characters based on whether they have active player links"""
        if value:
            # is_npc=True means NO active player link
            return queryset.exclude(links__is_active=True)
        else:
            # is_npc=False means HAS active player link
            return queryset.filter(links__is_active=True)
