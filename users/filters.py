# gameplay/filters.py
import django_filters
from django.conf import settings

from django.db.models import Q
from .models import Player


class PlayerFilter(django_filters.FilterSet):
    level = django_filters.RangeFilter(field_name="level")
    xp = django_filters.RangeFilter(field_name="xp")
    is_premium = django_filters.BooleanFilter(method="filter_is_premium")
    onboarding_step = django_filters.NumberFilter(field_name="onboarding_step")
    login_streak = django_filters.RangeFilter(method="filter_login_streak")

    def filter_is_premium(self, queryset, name, value):
        if value is None:
            return queryset

        premium_price_ids = {
            getattr(settings, "STRIPE_PRICE_ID_PREMIUM_MONTHLY", ""),
            getattr(settings, "STRIPE_PRICE_ID_PREMIUM_ANNUAL", ""),
        }
        premium_price_ids.discard("")

        premium_q = Q(user__subscriptions__active=True)
        if premium_price_ids:
            premium_q &= Q(
                user__subscriptions__plan__stripe_price_id__in=premium_price_ids
            )
        else:
            premium_q &= Q(pk__in=[])

        if value:
            return queryset.filter(premium_q).distinct()
        return queryset.exclude(premium_q).distinct()

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
