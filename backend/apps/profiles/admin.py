from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Skill, StudentProfile, EmployerProfile


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "name_en", "category", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("name", "name_en")


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "university", "field_of_study", "degree", "availability", "average_rating")
    list_filter = ("degree", "availability")
    search_fields = ("user__email", "user__full_name", "university")
    filter_horizontal = ("skills",)
    readonly_fields = ("created_at", "updated_at", "total_projects_completed", "average_rating")


@admin.register(EmployerProfile)
class EmployerProfileAdmin(admin.ModelAdmin):
    list_display = ("organization_name", "organization_type", "user", "city", "average_rating")
    list_filter = ("organization_type",)
    search_fields = ("organization_name", "user__email", "city")
    readonly_fields = ("created_at", "updated_at", "total_projects_posted", "total_hires")
