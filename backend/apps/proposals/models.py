"""
Proposal models for Research Marketplace.

A Student submits a Proposal to an open Project.

Lifecycle:
  PENDING → ACCEPTED → (project goes IN_PROGRESS)
           → REJECTED
           → WITHDRAWN (by student)
"""
import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator


class Proposal(models.Model):
    """
    A student's bid on a project.

    Key design decisions:
    - One proposal per student per project (unique_together)
    - Cover letter + proposed price + timeline
    - Admin can see all proposals; employer sees only their project's proposals
    """

    class Status(models.TextChoices):
        PENDING = "pending", _("در انتظار بررسی")
        ACCEPTED = "accepted", _("پذیرفته شده")
        REJECTED = "rejected", _("رد شده")
        WITHDRAWN = "withdrawn", _("پس گرفته شده")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="proposals",
        verbose_name=_("پروژه"),
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="submitted_proposals",
        limit_choices_to={"role": "student"},
        verbose_name=_("دانشجو"),
    )

    # --- Proposal Content ---
    cover_letter = models.TextField(max_length=3000, verbose_name=_("نامه معرفی"))
    proposed_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name=_("قیمت پیشنهادی (تومان)"),
    )
    proposed_duration_days = models.PositiveIntegerField(verbose_name=_("مدت زمان پیشنهادی (روز)"))
    relevant_experience = models.TextField(blank=True, max_length=2000, verbose_name=_("تجربه مرتبط"))
    portfolio_link = models.URLField(blank=True, verbose_name=_("لینک نمونه‌کار"))

    # --- Status ---
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        verbose_name=_("وضعیت"),
    )
    employer_note = models.TextField(blank=True, max_length=1000, verbose_name=_("یادداشت کارفرما"))

    # --- Timestamps ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("تاریخ بررسی"))

    class Meta:
        verbose_name = _("پیشنهاد")
        verbose_name_plural = _("پیشنهادها")
        ordering = ["-created_at"]
        unique_together = [["project", "student"]]
        indexes = [
            models.Index(fields=["project", "status"]),
            models.Index(fields=["student", "status"]),
        ]

    def __str__(self):
        return f"Proposal({self.student.full_name} → {self.project.title})"

    def accept(self):
        """Accept this proposal and start the project."""
        from django.utils import timezone
        self.status = self.Status.ACCEPTED
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "reviewed_at", "updated_at"])

        # Reject all other pending proposals for this project
        self.project.proposals.exclude(id=self.id).filter(
            status=self.Status.PENDING
        ).update(status=self.Status.REJECTED)

        # Trigger project start
        self.project.start(self.student, self.proposed_price)

    def reject(self, note: str = ""):
        from django.utils import timezone
        self.status = self.Status.REJECTED
        self.employer_note = note
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "employer_note", "reviewed_at", "updated_at"])

    def withdraw(self):
        self.status = self.Status.WITHDRAWN
        self.save(update_fields=["status", "updated_at"])


class Message(models.Model):
    """
    Simple in-project messaging between employer and hired student.
    Full chat with WebSocket is Phase 4 — this covers the data model.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name=_("پروژه"),
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_messages",
        verbose_name=_("فرستنده"),
    )
    body = models.TextField(max_length=5000, verbose_name=_("متن پیام"))
    attachment = models.FileField(upload_to="message_attachments/%Y/%m/", null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("پیام")
        verbose_name_plural = _("پیام‌ها")
        ordering = ["created_at"]

    def __str__(self):
        return f"Message({self.sender.full_name} → Project:{self.project_id})"
