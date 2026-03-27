import logging
from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

# log
logger = logging.getLogger('audit')

User = get_user_model()

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """
    Enregistre lorsqu'un utilisateur réussi à se connecter.
    """
    ip = request.META.get('REMOTE_ADDR')
    logger.info(f"LOGIN SUCCESS: User '{user.username}' (ID: {user.pk}) from IP {ip}")

@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    """
    Enregistre lorsqu'un utilisateur échoue à se connecter.
    """
    ip = request.META.get('REMOTE_ADDR')
    username = credentials.get('username', 'unknown')
    logger.warning(f"LOGIN FAILED: Username '{username}' from IP {ip}")

@receiver(post_save, sender=User)
def log_user_changes(sender, instance, created, dir_created=None, **kwargs):
    """
    Enregistre les modifications importantes d'un compte utilisateur (droits d'administrateur, statut).

    - Si le premier superuser est créé, lui ajoute automatiquement le groupe CEO.
    """
    if created:
        logger.info(f"USER CREATED: '{instance.username}' (ID: {instance.pk})")

        if instance.is_superuser:
            # S'il n'existe aucun superuser autre que lui, on le marque CEO
            other_superusers = User.objects.filter(is_superuser=True).exclude(pk=instance.pk).exists()
            if not other_superusers:
                from django.contrib.auth.models import Group
                ceo_group, _ = Group.objects.get_or_create(name='CEO')
                instance.groups.add(ceo_group)
                logger.info(f"FIRST SUPERUSER: '{instance.username}' a été attribué au groupe CEO.")
    else:
        if instance.is_superuser:
            logger.info(f"USER UPDATE: '{instance.username}' is now SUPERUSER")
