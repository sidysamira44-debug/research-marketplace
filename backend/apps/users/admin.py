"""Admin configuration for User model."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "email", "full_name", "role_badge", "is_verified",
        "is_active", "date_joined", "last_seen",
    )
    list_filter = ("role", "is_verified", "is_active", "is_deleted", "date_joined")
    search_fields = ("email", "full_name", "phone_number")
    ordering = ("-date_joined",)
    readonly_fields = ("id", "date_joined", "last_seen", "verified_at")

    fieldsets = (
        (_("اطلاعات ورود"), {"fields": ("id", "email", "password")}),
        (_("اطلاعات شخصی"), {"fields": ("full_name", "phone_number", "avatar")}),
        (_("نقش و دسترسی"), {"fields": ("role", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("وضعیت تأیید"), {"fields": ("is_verified", "verified_at", "is_deleted")}),
        (_("زمان‌ها"), {"fields": ("date_joined", "last_seen")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "full_name", "role", "password1", "password2"),
        }),
    )

    actions = ["verify_users", "suspend_users", "restore_users"]

    def role_badge(self, obj):
        colors = {
            "student": "#3B82F6",
            "employer": "#10B981",
            "admin": "#EF4444",
        }
        color = colors.get(obj.role, "#6B7280")
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:4px;font-size:11px">{}</span>',
            color, obj.get_role_display()
        )
    role_badge.short_description = _("نقش")

    @admin.action(description=_("تأیید کاربران انتخاب شده"))
    def verify_users(self, request, queryset):
        for user in queryset:
            user.verify()
        self.message_user(request, f"{queryset.count()} کاربر تأیید شد.")

    @admin.action(description=_("تعلیق کاربران انتخاب شده"))
    def suspend_users(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"{queryset.count()} کاربر تعلیق شد.")

    @admin.action(description=_("بازگرداندن کاربران حذف‌شده"))
    def restore_users(self, request, queryset):
        for user in queryset:
            user.restore()
        self.message_user(request, f"{queryset.count()} کاربر بازگردانده شد.")
