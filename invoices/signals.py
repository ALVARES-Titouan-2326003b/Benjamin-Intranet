from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import Group, User
from .models import Facture, FactureHistorique
from .services.email import send_invoice_status_email

# Garantit l'existence du groupe "POLE_FINANCIER" au démarrage
@receiver(post_save, sender=User)
def ensure_groups(sender, instance, created, **kwargs):
    """
    Crée les groupes associés aux pôles au démarrage s'ils n'existent pas.
    """
    for name in ['POLE_FINANCIER', 'POLE_TECHNIQUE', 'POLE_ADMINISTRATIF', 'CEO', 'COLLABORATEUR']:
        Group.objects.get_or_create(name=name)

@receiver(pre_save, sender=Facture)
def invoice_status_change_monitor(sender, instance, **kwargs):
    """
    Envoie un email lors du changement de statut de la facture
    """
    if instance.pk:
        try:
            old_instance = Facture.objects.get(pk=instance.pk)
            if old_instance.statut != instance.statut:
                # Status changed
                FactureHistorique.objects.create(
                    facture=instance,
                    action='status_change',
                    old_status=old_instance.statut,
                    new_status=instance.statut,
                    details=f"Statut modifié de {old_instance.statut} vers {instance.statut}",
                )
                send_invoice_status_email(instance, old_instance.statut, instance.statut)
        except Facture.DoesNotExist:
            pass
 