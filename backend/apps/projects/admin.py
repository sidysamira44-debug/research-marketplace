from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import ProjectCategory, Project, ProjectAttachment, Review


@admin.register(ProjectCategory)
class ProjectCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "name_en", "icon", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "name_en")


class ProjectAttachmentInline(admin.TabularInline):
    model = ProjectAttachment
    extra = 0
    readonly_fields = ("uploaded_at",)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "title", "employer", "category", "status_badge",
        "budget_display", "proposals_count", "is_featured", "created_at",
    )
    list_filter = ("status", "experience_level", "project_type", "is_featured", "category")
    search_fields = ("title", "employer__email", "employer__full_name")
    filter_horizontal = ("required_skills",)
    readonly_fields = ("created_at", "updated_at", "views_count", "proposals_count")
    inlines = [ProjectAttachmentInline]
    actions = ["feature_projects", "publish_projects"]

    def status_badge(self, obj):
        colors = {
            "draft": "#9CA3AF", "open": "#10B981", "in_progress": "#3B82F6",
            "completed": "#6366F1", "cancelled": "#EF4444", "disputed": "#F59E0B",
        }
        color = colors.get(obj.status, "#6B7280")
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:4px;font-size:11px">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = _("وضعیت")

    @admin.action(description=_("ویژه کردن پروژه‌های انتخاب‌شده"))
    def feature_projects(self, request, queryset):
        queryset.update(is_featured=True)

    @admin.action(description=_("انتشار پروژه‌های انتخاب‌شده"))
    def publish_projects(self, request, queryset):
        for project in queryset.filter(status="draft"):
            project.publish()


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("project", "reviewer", "reviewee", "rating", "created_at")
    list_filter = ("rating",)
    readonly_fields = ("created_at",)
