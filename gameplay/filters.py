import django_filters
from .models import Quest


class QuestFilter(django_filters.FilterSet):
    duration_choices = django_filters.CharFilter(
        field_name="duration_choices", lookup_expr="icontains"
    )
    stages_fixed = django_filters.BooleanFilter(field_name="stages_fixed")

    class Meta:
        model = Quest
        fields = ["duration_choices", "stages_fixed"]
