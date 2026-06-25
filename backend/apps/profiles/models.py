"""
Profile models for Research Marketplace.

Two profile types:
  - StudentProfile  : academic info, skills, resume, portfolio
  - EmployerProfile : organization info, verification documents

Both are created automatically via signals when a User is registered.
"""
import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator


class Skill(models.Model):
    """
    Reusable skill/tag entity shared across student profiles and projects.
    Examples: Machine Learning, Data Analysis, Python, Bioinformatics
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, verbose_name=_("مهارت"))
    name_en = models.CharField(max_length=100, blank=True, verbose_name=_("نام انگلیسی"))
    category = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("دسته‌بندی"),
        help_text=_("مثال: برنامه‌نویسی، بیوانفورماتیک، آمار"),
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("مهارت")
        verbose_name_plural = _("مهارت‌ها")
        ordering = ["name"]

    def __str__(self):
        return self.name


class StudentProfile(models.Model):
    """
    Extended profile for STUDENT role users.

    Academic background, skills, GPA, and portfolio links
    are used to match students with relevant projects.
    """

    class AvailabilityStatus(models.TextChoices):
        AVAILABLE = "available", _("آماده همکاری")
        BUSY = "busy", _("مشغول")
        PART_TIME = "part_time", _("پاره وقت")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_profile",
        verbose_name=_("کاربر"),
    )

    # --- Academic Info ---
    university = models.CharField(max_length=255, blank=True, verbose_name=_("دانشگاه"))
    field_of_study = models.CharField(max_length=255, blank=True, verbose_name=_("رشته تحصیلی"))
    degree = models.CharField(
        max_length=50,
        choices=[
            ("bachelor", _("کارشناسی")),
            ("master", _("کارشناسی ارشد")),
            ("phd", _("دکترا")),
            ("postdoc", _("پست دکترا")),
        ],
        blank=True,
        verbose_name=_("مقطع تحصیلی"),
    )
    gpa = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(20)],
        verbose_name=_("معدل"),
    )
    graduation_year = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name=_("سال فارغ‌التحصیلی"))

    # --- Skills & Expertise ---
    skills = models.ManyToManyField(
        Skill,
        blank=True,
        related_name="students",
        verbose_name=_("مهارت‌ها"),
    )
    bio = models.TextField(blank=True, max_length=2000, verbose_name=_("درباره من"))
    research_interests = models.TextField(blank=True, verbose_name=_("حوزه‌های پژوهشی"))

    # --- Files ---
    resume = models.FileField(
        upload_to="resumes/%Y/%m/",
        null=True,
        blank=True,
        verbose_name=_("رزومه"),
    )
    portfolio_url = models.URLField(blank=True, verbose_name=_("لینک پورتفولیو"))
    github_url = models.URLField(blank=True, verbose_name=_("گیت‌هاب"))
    linkedin_url = models.URLField(blank=True, verbose_name=_("لینکدین"))

    # --- Status ---
    availability = models.CharField(
        max_length=20,
        choices=AvailabilityStatus.choices,
        default=AvailabilityStatus.AVAILABLE,
        verbose_name=_("وضعیت پذیرش"),
    )
    hourly_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name=_("نرخ ساعتی (تومان)"),
    )

    # --- Stats (denormalized for performance) ---
    total_projects_completed = models.PositiveIntegerField(default=0)
    average_rating = models.DecimalField(
        max_digits=3, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
    )

    # --- Timestamps ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("پروفایل دانشجو")
        verbose_name_plural = _("پروفایل دانشجویان")

    def __str__(self):
        return f"StudentProfile({self.user.full_name})"


class EmployerProfile(models.Model):
    """
    Extended profile for EMPLOYER role users.

    Organization info and verification documents.
    Admin must verify the organization before they can post projects.
    """

    class OrganizationType(models.TextChoices):
        UNIVERSITY = "university", _("دانشگاه")
        RESEARCH_CENTER = "research_center", _("مرکز تحقیقاتی")
        STARTUP = "startup", _("استارتاپ")
        COMPANY = "company", _("شرکت")
        NGO = "ngo", _("سازمان غیرانتفاعی")
        GOVERNMENT = "government", _("دولتی")
        OTHER = "other", _("سایر")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="employer_profile",
        verbose_name=_("کاربر"),
    )

    # --- Organization Info ---
    organization_name = models.CharField(max_length=255, verbose_name=_("نام سازمان"))
    organization_type = models.CharField(
        max_length=30,
        choices=OrganizationType.choices,
        default=OrganizationType.COMPANY,
        verbose_name=_("نوع سازمان"),
    )
    description = models.TextField(blank=True, max_length=3000, verbose_name=_("توضیحات سازمان"))
    website = models.URLField(blank=True, verbose_name=_("وب‌سایت"))
    logo = models.ImageField(upload_to="logos/%Y/%m/", null=True, blank=True, verbose_name=_("لوگو"))

    # --- Location ---
    city = models.CharField(max_length=100, blank=True, verbose_name=_("شهر"))
    province = models.CharField(max_length=100, blank=True, verbose_name=_("استان"))

    # --- Verification ---
    registration_number = models.CharField(max_length=50, blank=True, verbose_name=_("شماره ثبت"))
    verification_document = models.FileField(
        upload_to="verification_docs/%Y/%m/",
        null=True,
        blank=True,
        verbose_name=_("مدرک تأییدیه"),
    )

    # --- Stats ---
    total_projects_posted = models.PositiveIntegerField(default=0)
    total_hires = models.PositiveIntegerField(default=0)
    average_rating = models.DecimalField(
        max_digits=3, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
    )

    # --- Timestamps ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("پروفایل کارفرما")
        verbose_name_plural = _("پروفایل کارفرمایان")

    def __str__(self):
        return f"EmployerProfile({self.organization_name})"
