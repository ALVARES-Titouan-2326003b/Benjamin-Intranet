"""Rôles métier transversaux de l'intranet."""

CEO_GROUP = "CEO"
EXECUTIVE_ASSISTANT_GROUP = "ASSISTANTE_DIRECTION"


def _is_authenticated(user):
    return bool(user and getattr(user, "is_authenticated", False))


def has_group(user, group_name):
    return _is_authenticated(user) and user.groups.filter(name=group_name).exists()


def is_ceo(user):
    """Le rôle CEO est explicite et distinct du superutilisateur technique."""
    return has_group(user, CEO_GROUP)


def has_direction_access(user):
    """Pouvoirs globaux du CEO et des comptes techniques de secours."""
    return _is_authenticated(user) and (user.is_superuser or is_ceo(user))


def is_executive_assistant(user):
    """Accès transversal en lecture, sans privilèges techniques de superutilisateur."""
    return has_group(user, EXECUTIVE_ASSISTANT_GROUP)


def has_global_read_access(user):
    return has_direction_access(user) or is_executive_assistant(user)
