# gameplay/filters.py
import django_filters
from .models import Profile


class ProfileFilter(django_filters.FilterSet):
    level = django_filters.RangeFilter(field_name="level")
    xp = django_filters.RangeFilter(field_name="xp")
    is_premium = django_filters.BooleanFilter(field_name="is_premium")
    onboarding_step = django_filters.NumberFilter(field_name="onboarding_step")
    login_streak = django_filters.RangeFilter(field_name="login_streak")

    class Meta:
        model = Profile
        fields = ["level", "xp", "is_premium", "onboarding_step", "login_streak"]
