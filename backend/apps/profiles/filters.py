"""django-filter FilterSets for profile search."""
import django_filters
from .models import StudentProfile, Skill


class StudentProfileFilter(django_filters.FilterSet):
    skill = django_filters.ModelMultipleChoiceFilter(
        field_name="skills",
        queryset=Skill.objects.filter(is_active=True),
        label="مهارت",
    )
    skill_name = django_filters.CharFilter(field_name="skills__name", lookup_expr="icontains")
    availability = django_filters.ChoiceFilter(choices=StudentProfile.AvailabilityStatus.choices)
    degree = django_filters.CharFilter(lookup_expr="exact")
    min_rating = django_filters.NumberFilter(field_name="average_rating", lookup_expr="gte")
    max_hourly_rate = django_filters.NumberFilter(field_name="hourly_rate", lookup_expr="lte")
    university = django_filters.CharFilter(lookup_expr="icontains")
    field_of_study = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = StudentProfile
        fields = ["availability", "degree", "university", "field_of_study"]
