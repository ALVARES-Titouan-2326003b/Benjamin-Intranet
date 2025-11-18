"""
Configuration Celery pour Benjamin Immobilier
"""
import os
from celery import Celery

# Définit le module de settings Django par défaut
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Crée l'instance Celery
app = Celery('Proj')

# Charge la configuration depuis les settings Django avec le préfixe CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Découvre automatiquement les tâches dans les apps Django
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')