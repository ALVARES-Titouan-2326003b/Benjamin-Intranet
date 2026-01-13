"""
Configuration Celery pour Benjamin Immobilier
"""
import os
from celery import Celery
from celery.schedules import crontab


# Définit le module de settings Django par défaut
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Crée l'instance Celery
app = Celery('celery')

# Charge la configuration depuis les settings Django avec le préfixe CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Découvre automatiquement les tâches dans les apps Django
app.autodiscover_tasks()

# ============================================================================
# CONFIGURATION DE CELERY BEAT (PLANIFICATEUR DE TÂCHES)
# ============================================================================

app.conf.beat_schedule = {
    'check-and-send-auto-relances': {
        'task': 'management.tasks.check_and_send_auto_relances',
        'schedule': crontab(minute='*/5'),
    },
    'check-activite-reminders-daily': {
        'task': 'management.tasks.check_and_send_activite_reminders',
        'schedule': crontab(minute='*/5'),
    },
    'check-and-send-invoice-reminders': {
        'task': 'invoices.tasks.check_and_send_invoice_reminders',
        'schedule': crontab(minute='*/5'),
    },
}
app.conf.timezone = 'Europe/Paris'


# ============================================================================
# TÂCHE DE DEBUG (OPTIONNELLE)
# ============================================================================

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """
    Tâche de debug pour tester que Celery fonctionne correctement

    Usage depuis le shell Django :
    >>> from config.celery import debug_task
    >>> debug_task.delay()
    """
    print(f'Request: {self.request!r}')