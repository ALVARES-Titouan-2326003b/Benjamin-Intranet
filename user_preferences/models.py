from django.db import models
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

User = get_user_model()

class UserPreference(models.Model):
    THEME_CHOICES = [
        ('light', 'Clair'),
        ('dark', 'Sombre'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preferences')
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default='light', verbose_name="Thème")

    def __str__(self):
        return f"Préférences de {self.user.username}"

@receiver(post_save, sender=User)
def create_user_preferences(sender, instance, created, **kwargs):
    if created:
        UserPreference.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_preferences(sender, instance, **kwargs):
    # Ensure preference object exists just in case
    if not hasattr(instance, 'preferences'):
        UserPreference.objects.create(user=instance)
    instance.preferences.save()
