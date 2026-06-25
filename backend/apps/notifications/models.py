"""
Notification model for Research Marketplace.

In-app notifications triggered by system events:
  - New proposal received
  - Proposal accepted/rejected
  - Project completed
  - Payment released
  - Dispute raised/resolved
  - Admin verification approved

Delivery: stored in DB + optionally sent via Celery (email/push in Phase 4).
"""
import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Notification(models.Model):

    class NotificationType(models.TextChoices):
        PROPOSAL_RECEIVED = "proposal_received", _("پیشنهاد جدید")
        PROPOSAL_ACCEPTED = "proposal_accepted", _("پیشنهاد پذیرفته شد")
        PROPOSAL_REJECTED = "proposal_rejected", _("پیشنهاد رد شد")
        PROJECT_STARTED = "project_started", _("پروژه شروع شد")
        PROJECT_COMPLETED = "project_completed", _("پروژه تکمیل شد")
        PAYMENT_RELEASED = "payment_released", _("وجه آزاد شد")
        DISPUTE_RAISED = "dispute_raised", _("اختلاف ثبت شد")
        DISPUTE_RESOLVED = "dispute_resolved", _("اختلاف حل شد")
        ACCOUNT_VERIFIED = "account_verified", _("حساب تأیید شد")
        NEW_MESSAGE = "new_message", _("پیام جدید")
        REVIEW_RECEIVED = "review_received", _("نظر جدید دریافت شد")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("دریافت‌کننده"),
    )
    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
        db_index=True,
        verbose_name=_("نوع اعلان"),
    )
    title = models.CharField(max_length=255, verbose_name=_("عنوان"))
    body = models.TextField(verbose_name=_("متن"))

    # Generic FK to the related object (project, proposal, etc.)
    related_object_id = models.UUIDField(null=True, blank=True, verbose_name=_("شناسه شیء مرتبط"))
    related_object_type = models.CharField(max_length=50, blank=True, verbose_name=_("نوع شیء"))

    is_read = models.BooleanField(default=False, db_index=True, verbose_name=_("خوانده شده"))
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("اعلان")
        verbose_name_plural = _("اعلان‌ها")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
        ]

    def __str__(self):
        return f"[{self.get_notification_type_display()}] → {self.recipient.full_name}"

    def mark_read(self):
        from django.utils import timezone
        self.is_read = True
        self.read_at = timezone.now()
        self.save(update_fields=["is_read", "read_at"])

    @classmethod
    def send(cls, recipient, notification_type, title, body, related_object_id=None, related_object_type=""):
        """Factory method to create a notification."""
        return cls.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            body=body,
            related_object_id=related_object_id,
            related_object_type=related_object_type,
        )
