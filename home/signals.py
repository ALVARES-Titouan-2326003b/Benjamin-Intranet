from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django_otp.plugins.otp_email.models import EmailDevice

User = get_user_model()

@receiver(post_save, sender=User)
def create_email_device(sender, instance, created, **kwargs):
    """
    Chaque utilisateur va devoir passer par la vérification de 2FA pour pouvoir se connecter.
    """
    if created or not EmailDevice.objects.filter(user=instance).exists():
        if instance.email:
            device, _ = EmailDevice.objects.get_or_create(
                user=instance,
                name='Default Email',
                defaults={'email': instance.email, 'confirmed': True}
            )
            if not device.confirmed:
                device.confirmed = True
                device.save()
