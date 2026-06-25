"""
Payment models for Research Marketplace.

Flow:
  1. Employer funds an Escrow when hiring a student (Stripe PaymentIntent).
  2. Platform holds funds until project is COMPLETED.
  3. On completion: platform releases funds to student (minus commission).
  4. Commission is auto-calculated from settings.PLATFORM_COMMISSION_PERCENT.

Transaction types:
  - ESCROW_HOLD   : employer pays into escrow
  - RELEASE       : funds released to student
  - REFUND        : escrow refunded to employer on cancellation
  - COMMISSION    : platform fee deducted
"""
import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator


class Transaction(models.Model):
    """
    Financial transaction record tied to a Project.
    Each escrow/release/refund creates one Transaction row.
    Stripe IDs are stored for reconciliation.
    """

    class TransactionType(models.TextChoices):
        ESCROW_HOLD = "escrow_hold", _("بلوکه در امانت")
        RELEASE = "release", _("آزادسازی وجه")
        REFUND = "refund", _("بازگشت وجه")
        COMMISSION = "commission", _("کارمزد پلتفرم")

    class Status(models.TextChoices):
        PENDING = "pending", _("در انتظار")
        COMPLETED = "completed", _("موفق")
        FAILED = "failed", _("ناموفق")
        REFUNDED = "refunded", _("بازگشت داده شده")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # --- Parties ---
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.PROTECT,
        related_name="transactions",
        verbose_name=_("پروژه"),
    )
    payer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="outgoing_transactions",
        verbose_name=_("پرداخت‌کننده"),
    )
    payee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="incoming_transactions",
        verbose_name=_("دریافت‌کننده"),
    )

    # --- Amounts ---
    gross_amount = models.DecimalField(
        max_digits=15, decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name=_("مبلغ ناخالص (تومان)"),
    )
    commission_amount = models.DecimalField(
        max_digits=15, decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_("کارمزد پلتفرم (تومان)"),
    )
    net_amount = models.DecimalField(
        max_digits=15, decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name=_("مبلغ خالص (تومان)"),
    )
    commission_percent = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=10.00,
        verbose_name=_("درصد کارمزد"),
    )

    # --- Type & Status ---
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
        db_index=True,
        verbose_name=_("نوع تراکنش"),
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        verbose_name=_("وضعیت"),
    )

    # --- Stripe Fields ---
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, db_index=True)
    stripe_transfer_id = models.CharField(max_length=255, blank=True)
    stripe_refund_id = models.CharField(max_length=255, blank=True)
    stripe_error_message = models.TextField(blank=True)

    # --- Meta ---
    description = models.TextField(blank=True, verbose_name=_("توضیحات"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("تراکنش")
        verbose_name_plural = _("تراکنش‌ها")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["project", "transaction_type"]),
            models.Index(fields=["status", "transaction_type"]),
        ]

    def __str__(self):
        return f"{self.get_transaction_type_display()} | {self.gross_amount:,.0f}T | {self.get_status_display()}"

    def save(self, *args, **kwargs):
        """Auto-calculate net amount before saving."""
        if not self.net_amount:
            self.net_amount = self.gross_amount - self.commission_amount
        super().save(*args, **kwargs)


class Dispute(models.Model):
    """
    Raised when employer or student has a conflict on a project.
    Admin reviews and resolves disputes.
    """

    class Resolution(models.TextChoices):
        PENDING = "pending", _("در انتظار بررسی")
        RESOLVED_FOR_EMPLOYER = "resolved_employer", _("به نفع کارفرما")
        RESOLVED_FOR_STUDENT = "resolved_student", _("به نفع دانشجو")
        SPLIT = "split", _("تقسیم وجه")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.OneToOneField(
        "projects.Project",
        on_delete=models.PROTECT,
        related_name="dispute",
        verbose_name=_("پروژه"),
    )
    raised_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="raised_disputes",
        verbose_name=_("مطرح‌کننده"),
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_disputes",
        limit_choices_to={"role": "admin"},
        verbose_name=_("ادمین رسیدگی‌کننده"),
    )

    reason = models.TextField(verbose_name=_("دلیل اختلاف"))
    resolution = models.CharField(
        max_length=30,
        choices=Resolution.choices,
        default=Resolution.PENDING,
        verbose_name=_("نتیجه"),
    )
    admin_note = models.TextField(blank=True, verbose_name=_("یادداشت ادمین"))

    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("اختلاف")
        verbose_name_plural = _("اختلافات")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Dispute on {self.project.title} [{self.get_resolution_display()}]"
