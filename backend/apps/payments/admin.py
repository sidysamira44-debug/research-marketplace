from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import Transaction, Dispute


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "project", "transaction_type", "gross_amount", "commission_amount",
        "net_amount", "status_badge", "created_at",
    )
    list_filter = ("transaction_type", "status")
    search_fields = ("project__title", "payer__email", "stripe_payment_intent_id")
    readonly_fields = (
        "id", "created_at", "updated_at", "completed_at",
        "stripe_payment_intent_id", "stripe_transfer_id", "stripe_refund_id",
    )

    def status_badge(self, obj):
        colors = {
            "pending": "#F59E0B", "completed": "#10B981",
            "failed": "#EF4444", "refunded": "#6366F1",
        }
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:4px;font-size:11px">{}</span>',
            colors.get(obj.status, "#6B7280"), obj.get_status_display()
        )
    status_badge.short_description = _("وضعیت")


@admin.register(Dispute)
class DisputeAdmin(admin.ModelAdmin):
    list_display = ("project", "raised_by", "resolution", "resolved_by", "created_at")
    list_filter = ("resolution",)
    search_fields = ("project__title", "raised_by__email")
    readonly_fields = ("created_at", "resolved_at")
