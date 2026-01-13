import logging
from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model

# log
logger = logging.getLogger('audit')

User = get_user_model()

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    ip = request.META.get('REMOTE_ADDR')
    logger.info(f"LOGIN SUCCESS: User '{user.username}' (ID: {user.pk}) from IP {ip}")

@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    ip = request.META.get('REMOTE_ADDR')
    username = credentials.get('username', 'unknown')
    logger.warning(f"LOGIN FAILED: Username '{username}' from IP {ip}")

@receiver(post_save, sender=User)
def log_user_changes(sender, instance, created, dir_created=None, **kwargs):
    """Log sensitive changes to user accounts (admin rights, status)."""
    if created:
        logger.info(f"USER CREATED: '{instance.username}' (ID: {instance.pk})")
    else:
        if instance.is_superuser:
             logger.info(f"USER UPDATE: '{instance.username}' is now SUPERUSER")
