"""
Custom User Model for Research Marketplace.

Replaces Django's default User with a role-based system:
  - STUDENT  : can browse projects, submit proposals, manage profile
  - EMPLOYER : can post projects, review proposals, hire students
  - ADMIN    : platform management, dispute resolution, analytics

Design decisions:
  - AbstractBaseUser for full control (username replaced by email)
  - PermissionsMixin for standard Django permissions
  - Soft delete via `is_deleted` flag (preserve data integrity)
  - Verification flow: users must be verified before posting/hiring
"""
import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UserRole(models.TextChoices):
    STUDENT = "student", _("دانشجو")
    EMPLOYER = "employer", _("کارفرما")
    ADMIN = "admin", _("مدیر")


class UserManager(BaseUserManager):
    """
    Custom manager using email as the unique identifier instead of username.
    """

    def _create_user(self, email: str, password: str, **extra_fields):
        if not email:
            raise ValueError(_("ایمیل الزامی است"))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str = None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", UserRole.ADMIN)
        extra_fields.setdefault("is_verified", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self._create_user(email, password, **extra_fields)

    def get_queryset(self):
        """Exclude soft-deleted users from all default queries."""
        return super().get_queryset().filter(is_deleted=False)

    def with_deleted(self):
        """Include soft-deleted users (admin use only)."""
        return super().get_queryset()


class User(AbstractBaseUser, PermissionsMixin):
    """
    Core User model. Email-based auth with role differentiation.

    Fields:
        id          : UUID PK (non-guessable)
        email       : unique login identifier
        role        : STUDENT | EMPLOYER | ADMIN
        is_verified : set True by admin after document check
        is_active   : False = suspended account
        is_deleted  : soft delete
        last_seen   : updated on each API request
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("شناسه"),
    )
    email = models.EmailField(
        unique=True,
        db_index=True,
        verbose_name=_("ایمیل"),
        error_messages={"unique": _("این ایمیل قبلاً ثبت شده است.")},
    )
    full_name = models.CharField(
        max_length=255,
        verbose_name=_("نام کامل"),
    )
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.STUDENT,
        db_index=True,
        verbose_name=_("نقش"),
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_("شماره تماس"),
    )
    avatar = models.ImageField(
        upload_to="avatars/%Y/%m/",
        blank=True,
        null=True,
        verbose_name=_("تصویر پروفایل"),
    )

    # --- Status Flags ---
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("فعال"),
        help_text=_("حساب‌های غیرفعال نمی‌توانند وارد شوند"),
    )
    is_staff = models.BooleanField(
        default=False,
        verbose_name=_("دسترسی به پنل ادمین"),
    )
    is_verified = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=_("تأیید شده"),
        help_text=_("توسط ادمین پس از بررسی مدارک تأیید می‌شود"),
    )
    is_deleted = models.BooleanField(
        default=False,
        verbose_name=_("حذف شده"),
        help_text=_("حذف نرم — داده حفظ می‌شود"),
    )

    # --- Timestamps ---
    date_joined = models.DateTimeField(default=timezone.now, verbose_name=_("تاریخ عضویت"))
    last_seen = models.DateTimeField(null=True, blank=True, verbose_name=_("آخرین بازدید"))
    verified_at = models.DateTimeField(null=True, blank=True, verbose_name=_("تاریخ تأیید"))

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name", "role"]

    class Meta:
        verbose_name = _("کاربر")
        verbose_name_plural = _("کاربران")
        ordering = ["-date_joined"]
        indexes = [
            models.Index(fields=["email", "role"]),
            models.Index(fields=["is_verified", "role"]),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} <{self.email}> [{self.get_role_display()}]"

    # --- Role Shortcuts ---
    @property
    def is_student(self) -> bool:
        return self.role == UserRole.STUDENT

    @property
    def is_employer(self) -> bool:
        return self.role == UserRole.EMPLOYER

    @property
    def is_platform_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    # --- Soft Delete ---
    def soft_delete(self):
        """Mark user as deleted without removing from DB."""
        self.is_deleted = True
        self.is_active = False
        self.save(update_fields=["is_deleted", "is_active"])

    def restore(self):
        """Restore a soft-deleted user."""
        self.is_deleted = False
        self.is_active = True
        self.save(update_fields=["is_deleted", "is_active"])

    # --- Verification ---
    def verify(self):
        """Mark user as verified (called by admin)."""
        self.is_verified = True
        self.verified_at = timezone.now()
        self.save(update_fields=["is_verified", "verified_at"])

    def update_last_seen(self):
        """Update last_seen timestamp (called from middleware)."""
        self.last_seen = timezone.now()
        self.save(update_fields=["last_seen"])
