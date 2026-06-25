"""
Signals for the users app.
- Post-save: send welcome email, create related profile.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender="users.User")
def user_post_save(sender, instance, created, **kwargs):
    if created:
        logger.info(f"New user registered: {instance.email} [{instance.role}]")
        # Profile creation is handled in profiles/signals.py to avoid circular imports
