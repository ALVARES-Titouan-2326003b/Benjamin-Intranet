"""
Settings spécifiques pour les tests
Hérite de settings.py mais utilise SQLite en mémoire
"""
from .settings import *  # noqa: F403,F401

DEBUG = True
CELERY_TASK_ALWAYS_EAGER = True

# Override de la base de données pour les tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Cache mémoire pour tester aussi les sondes de disponibilité.
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'benjamin-intranet-tests',
    }
}

# Optionnel : accélérer les tests en utilisant un hasher de mot de passe plus simple
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]
