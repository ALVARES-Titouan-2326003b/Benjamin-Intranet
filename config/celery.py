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
    # Tâche de relance automatique
    'check-and-send-auto-relances': {
        'task': 'management.tasks.check_and_send_auto_relances',

        # ⏰ FRÉQUENCE : Toutes les 5 minutes
        'schedule': crontab(minute='*/1'),

        # 📝 AUTRES EXEMPLES DE PLANIFICATION :
        #
        # Tous les jours à 9h00 :
        # 'schedule': crontab(hour=9, minute=0),
        #
        # Tous les jours à 14h30 :
        # 'schedule': crontab(hour=14, minute=30),
        #
        # Toutes les heures :
        # 'schedule': crontab(minute=0),
        #
        # Toutes les 30 minutes :
        # 'schedule': crontab(minute='*/30'),
        #
        # Toutes les 10 minutes :
        # 'schedule': crontab(minute='*/10'),
        #
        # Du lundi au vendredi à 9h00 :
        # 'schedule': crontab(hour=9, minute=0, day_of_week='1-5'),
        #
        # Uniquement les lundis à 10h00 :
        # 'schedule': crontab(hour=10, minute=0, day_of_week=1),
        #
        # Le 1er de chaque mois à 9h00 :
        # 'schedule': crontab(hour=9, minute=0, day_of_month=1),
    },
}

# Configuration du fuseau horaire
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