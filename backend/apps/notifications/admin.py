from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient", "notification_type", "title", "is_read", "created_at")
    list_filter = ("notification_type", "is_read")
    search_fields = ("recipient__email", "title")
    readonly_fields = ("created_at", "read_at")
    actions = ["mark_as_read"]

    @admin.action(description="علامت‌گذاری به عنوان خوانده شده")
    def mark_as_read(self, request, queryset):
        for n in queryset:
            n.mark_read()
