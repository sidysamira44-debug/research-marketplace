"""Serializers for payments app."""
from rest_framework import serializers
from .models import Transaction, Dispute
from apps.users.serializers import UserSerializer


class TransactionSerializer(serializers.ModelSerializer):
    payer = UserSerializer(read_only=True)
    payee = UserSerializer(read_only=True)
    transaction_type_display = serializers.CharField(source="get_transaction_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Transaction
        fields = [
            "id", "project", "payer", "payee",
            "gross_amount", "commission_amount", "net_amount", "commission_percent",
            "transaction_type", "transaction_type_display",
            "status", "status_display",
            "stripe_payment_intent_id",
            "description", "created_at", "completed_at",
        ]
        read_only_fields = fields


class DisputeSerializer(serializers.ModelSerializer):
    raised_by = UserSerializer(read_only=True)
    resolved_by = UserSerializer(read_only=True)
    resolution_display = serializers.CharField(source="get_resolution_display", read_only=True)

    class Meta:
        model = Dispute
        fields = [
            "id", "project", "raised_by", "resolved_by",
            "reason", "resolution", "resolution_display",
            "admin_note", "created_at", "resolved_at",
        ]
        read_only_fields = ["id", "raised_by", "resolved_by", "resolution", "admin_note", "created_at", "resolved_at"]


class CreatePaymentIntentSerializer(serializers.Serializer):
    """Input for Stripe PaymentIntent creation."""
    project_id = serializers.UUIDField()

    def validate_project_id(self, value):
        from apps.projects.models import Project
        try:
            project = Project.objects.get(id=value)
        except Project.DoesNotExist:
            raise serializers.ValidationError("پروژه یافت نشد.")
        if project.status != Project.Status.IN_PROGRESS:
            raise serializers.ValidationError("پرداخت فقط برای پروژه‌های در حال انجام مجاز است.")
        if not project.agreed_price:
            raise serializers.ValidationError("قیمت توافق‌شده برای این پروژه تعیین نشده است.")
        return project
