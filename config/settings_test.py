"""
Settings spécifiques pour les tests
Hérite de settings.py mais utilise SQLite en mémoire
"""
from .settings import *

# Override de la base de données pour les tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Optionnel : désactiver le cache pour les tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Optionnel : accélérer les tests en utilisant un hasher de mot de passe plus simple
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]