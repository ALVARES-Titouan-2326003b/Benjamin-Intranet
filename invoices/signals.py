from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import Group, User

# Garantit l'existence du groupe "POLE_FINANCIER" au démarrage
@receiver(post_save, sender=User)
def ensure_groups(sender, instance, created, **kwargs):
    Group.objects.get_or_create(name='POLE_FINANCIER')
 