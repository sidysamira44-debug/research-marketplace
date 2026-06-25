from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import Proposal, Message


@admin.register(Proposal)
class ProposalAdmin(admin.ModelAdmin):
    list_display = ("student", "project", "proposed_price", "status_badge", "created_at")
    list_filter = ("status",)
    search_fields = ("student__email", "student__full_name", "project__title")
    readonly_fields = ("created_at", "updated_at", "reviewed_at")
    actions = ["accept_proposals", "reject_proposals"]

    def status_badge(self, obj):
        colors = {
            "pending": "#F59E0B", "accepted": "#10B981",
            "rejected": "#EF4444", "withdrawn": "#9CA3AF",
        }
        color = colors.get(obj.status, "#6B7280")
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:4px;font-size:11px">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = _("وضعیت")

    @admin.action(description=_("پذیرش پیشنهادهای انتخاب‌شده"))
    def accept_proposals(self, request, queryset):
        for p in queryset.filter(status="pending"):
            p.accept()

    @admin.action(description=_("رد پیشنهادهای انتخاب‌شده"))
    def reject_proposals(self, request, queryset):
        for p in queryset.filter(status="pending"):
            p.reject()


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("sender", "project", "is_read", "created_at")
    list_filter = ("is_read",)
    readonly_fields = ("created_at",)
