"""Auto-create StudentProfile or EmployerProfile when a User is saved."""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from apps.users.models import UserRole
import logging

logger = logging.getLogger(__name__)

User = settings.AUTH_USER_MODEL


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    """
    When a new User is created, automatically create the matching profile.
    Import models here (not at module level) to avoid AppRegistryNotReady.
    """
    if not created:
        return

    from apps.profiles.models import StudentProfile, EmployerProfile

    if instance.role == UserRole.STUDENT:
        StudentProfile.objects.get_or_create(user=instance)
        logger.info(f"StudentProfile created for {instance.email}")

    elif instance.role == UserRole.EMPLOYER:
        EmployerProfile.objects.get_or_create(user=instance)
        logger.info(f"EmployerProfile created for {instance.email}")
