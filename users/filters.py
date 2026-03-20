# gameplay/filters.py
import django_filters
from .models import Player


class PlayerFilter(django_filters.FilterSet):
    level = django_filters.RangeFilter(field_name="level")
    xp = django_filters.RangeFilter(field_name="xp")
    is_premium = django_filters.BooleanFilter(field_name="is_premium")
    onboarding_step = django_filters.NumberFilter(field_name="onboarding_step")
    login_streak = django_filters.RangeFilter(method="filter_login_streak")

    def filter_login_streak(self, queryset, name, value):
        if value is None:
            return queryset

        start = getattr(value, "start", None)
        stop = getattr(value, "stop", None)
        matching_ids = []

        for player in queryset.select_related("user"):
            streak = player.user.current_login_streak
            if start is not None and streak < start:
                continue
            if stop is not None and streak > stop:
                continue
            matching_ids.append(player.id)

        return queryset.filter(id__in=matching_ids)

    class Meta:
        model = Player
        fields = ["level", "xp", "is_premium", "onboarding_step", "login_streak"]
