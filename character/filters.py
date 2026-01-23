# gameplay/filters.py
import django_filters
from .models import Character


class CharacterFilter(django_filters.FilterSet):
    level = django_filters.RangeFilter(field_name="level")
    xp = django_filters.RangeFilter(field_name="xp")
    can_link = django_filters.BooleanFilter(field_name="can_link")

    class Meta:
        model = Character
        fields = ["level", "xp", "can_link"]
