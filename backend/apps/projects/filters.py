"""FilterSets for project search & filtering."""
import django_filters
from .models import Project, ProjectCategory
from apps.profiles.models import Skill


class ProjectFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=Project.Status.choices)
    experience_level = django_filters.ChoiceFilter(choices=Project.ExperienceLevel.choices)
    project_type = django_filters.ChoiceFilter(choices=Project.ProjectType.choices)
    category = django_filters.ModelChoiceFilter(queryset=ProjectCategory.objects.filter(is_active=True))
    skill = django_filters.ModelMultipleChoiceFilter(
        field_name="required_skills",
        queryset=Skill.objects.filter(is_active=True),
    )
    skill_name = django_filters.CharFilter(field_name="required_skills__name", lookup_expr="icontains")
    min_budget = django_filters.NumberFilter(field_name="budget_min", lookup_expr="gte")
    max_budget = django_filters.NumberFilter(field_name="budget_max", lookup_expr="lte")
    is_featured = django_filters.BooleanFilter()
    deadline_after = django_filters.DateFilter(field_name="deadline", lookup_expr="gte")
    deadline_before = django_filters.DateFilter(field_name="deadline", lookup_expr="lte")

    class Meta:
        model = Project
        fields = ["status", "experience_level", "project_type", "category", "is_featured"]
