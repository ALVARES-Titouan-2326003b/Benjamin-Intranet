"""Champs de modèle pour les secrets stockés en base de données."""

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models


ENCRYPTED_PREFIX = "fernet:v1:"


def _cipher() -> MultiFernet:
    try:
        keys = settings.FIELD_ENCRYPTION_KEYS
        return MultiFernet([Fernet(key.encode("ascii")) for key in keys])
    except (AttributeError, TypeError, ValueError) as exc:
        raise ImproperlyConfigured(
            "FIELD_ENCRYPTION_KEY doit être une clé Fernet valide."
        ) from exc


def encrypt_value(value: str | None) -> str | None:
    if value is None or value == "" or value.startswith(ENCRYPTED_PREFIX):
        return value
    token = _cipher().encrypt(value.encode("utf-8")).decode("ascii")
    return f"{ENCRYPTED_PREFIX}{token}"


def decrypt_value(value: str | None) -> str | None:
    if value is None or value == "" or not value.startswith(ENCRYPTED_PREFIX):
        # Compatibilité de lecture durant la migration des anciennes valeurs en clair.
        return value
    token = value.removeprefix(ENCRYPTED_PREFIX)
    try:
        return _cipher().decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError(
            "Impossible de déchiffrer une valeur sensible : vérifiez les clés de rotation."
        ) from exc


class EncryptedTextField(models.TextField):
    """TextField chiffré avec Fernet, compatible avec les valeurs historiques en clair."""

    def from_db_value(self, value, expression, connection):
        return decrypt_value(value)

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        return encrypt_value(value)
