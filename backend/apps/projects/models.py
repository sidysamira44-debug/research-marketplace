"""
Project models for Research Marketplace.

Lifecycle:
  DRAFT → OPEN → IN_PROGRESS → COMPLETED | CANCELLED | DISPUTED

A Project is posted by an Employer.
Students submit Proposals to Projects.
Admin can intervene in DISPUTED state.
"""
import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator


class ProjectCategory(models.Model):
    """Top-level research category (e.g. Biotech, AI, Social Sciences)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150, unique=True, verbose_name=_("نام دسته"))
    name_en = models.CharField(max_length=150, blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text=_("نام آیکون (مثلاً: flask, brain)"))
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("دسته‌بندی پروژه")
        verbose_name_plural = _("دسته‌بندی‌های پروژه")
        ordering = ["name"]

    def __str__(self):
        return self.name


class Project(models.Model):
    """
    Core Project entity posted by Employers.

    Budget model: employers set min/max range.
    Duration: in days (e.g. 30, 60, 90).
    Required skills: M2M to Skill for matching.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", _("پیش‌نویس")
        OPEN = "open", _("باز")
        IN_PROGRESS = "in_progress", _("در حال انجام")
        COMPLETED = "completed", _("تکمیل شده")
        CANCELLED = "cancelled", _("لغو شده")
        DISPUTED = "disputed", _("در اختلاف")

    class ExperienceLevel(models.TextChoices):
        BEGINNER = "beginner", _("مبتدی")
        INTERMEDIATE = "intermediate", _("متوسط")
        ADVANCED = "advanced", _("پیشرفته")
        EXPERT = "expert", _("متخصص")

    class ProjectType(models.TextChoices):
        FULL_TIME = "full_time", _("تمام وقت")
        PART_TIME = "part_time", _("پاره وقت")
        ONE_TIME = "one_time", _("یک بار")
        ONGOING = "ongoing", _("مداوم")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # --- Relations ---
    employer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posted_projects",
        limit_choices_to={"role": "employer"},
        verbose_name=_("کارفرما"),
    )
    hired_student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hired_projects",
        limit_choices_to={"role": "student"},
        verbose_name=_("دانشجوی استخدام‌شده"),
    )
    category = models.ForeignKey(
        ProjectCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
        verbose_name=_("دسته‌بندی"),
    )
    required_skills = models.ManyToManyField(
        "profiles.Skill",
        blank=True,
        related_name="projects",
        verbose_name=_("مهارت‌های مورد نیاز"),
    )

    # --- Content ---
    title = models.CharField(max_length=255, verbose_name=_("عنوان پروژه"))
    description = models.TextField(verbose_name=_("توضیحات"))
    deliverables = models.TextField(blank=True, verbose_name=_("خروجی‌های مورد انتظار"))
    requirements = models.TextField(blank=True, verbose_name=_("پیش‌نیازها"))

    # --- Budget ---
    budget_min = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name=_("بودجه حداقل (تومان)"),
    )
    budget_max = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name=_("بودجه حداکثر (تومان)"),
    )
    agreed_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("قیمت توافق‌شده (تومان)"),
    )

    # --- Attributes ---
    duration_days = models.PositiveIntegerField(verbose_name=_("مدت زمان (روز)"))
    experience_level = models.CharField(
        max_length=20,
        choices=ExperienceLevel.choices,
        default=ExperienceLevel.INTERMEDIATE,
        verbose_name=_("سطح تجربه"),
    )
    project_type = models.CharField(
        max_length=20,
        choices=ProjectType.choices,
        default=ProjectType.ONE_TIME,
        verbose_name=_("نوع پروژه"),
    )

    # --- Status & Visibility ---
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
        verbose_name=_("وضعیت"),
    )
    is_featured = models.BooleanField(default=False, verbose_name=_("ویژه"))
    views_count = models.PositiveIntegerField(default=0)
    proposals_count = models.PositiveIntegerField(default=0)

    # --- Important Dates ---
    deadline = models.DateField(null=True, blank=True, verbose_name=_("مهلت ارسال پیشنهاد"))
    started_at = models.DateTimeField(null=True, blank=True, verbose_name=_("تاریخ شروع"))
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("تاریخ اتمام"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("پروژه")
        verbose_name_plural = _("پروژه‌ها")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["employer", "status"]),
            models.Index(fields=["category", "status"]),
        ]

    def __str__(self):
        return f"{self.title} [{self.get_status_display()}]"

    @property
    def budget_display(self):
        return f"{self.budget_min:,.0f} - {self.budget_max:,.0f} تومان"

    def publish(self):
        """Move project from DRAFT to OPEN."""
        self.status = self.Status.OPEN
        self.save(update_fields=["status", "updated_at"])

    def start(self, student, agreed_price):
        """Hire a student and start the project."""
        from django.utils import timezone
        self.hired_student = student
        self.agreed_price = agreed_price
        self.status = self.Status.IN_PROGRESS
        self.started_at = timezone.now()
        self.save(update_fields=["hired_student", "agreed_price", "status", "started_at", "updated_at"])

    def complete(self):
        from django.utils import timezone
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at", "updated_at"])

    def cancel(self):
        self.status = self.Status.CANCELLED
        self.save(update_fields=["status", "updated_at"])


class ProjectAttachment(models.Model):
    """Files attached to a project (specs, sample data, references)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="project_attachments/%Y/%m/")
    name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("پیوست پروژه")
        verbose_name_plural = _("پیوست‌های پروژه")

    def __str__(self):
        return f"{self.name} → {self.project.title}"


class Review(models.Model):
    """
    Mutual rating after project completion.
    Both employer → student and student → employer can leave reviews.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="reviews")
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="given_reviews")
    reviewee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_reviews")
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name=_("امتیاز"),
    )
    comment = models.TextField(blank=True, max_length=1000, verbose_name=_("نظر"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("نظر")
        verbose_name_plural = _("نظرات")
        unique_together = [["project", "reviewer"]]
        ordering = ["-created_at"]

    def __str__(self):
        return f"Review {self.rating}★ on {self.project.title}"
