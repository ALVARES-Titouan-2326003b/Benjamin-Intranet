from django.contrib.auth.models import User


def has_finance_access(user):
    """
    Renvoie vrai si un utilisateur peut accéder au pôle financier

    Args:
        user (User):  L'utilisateur
    """
    user = User.objects.get(username=user.username)
    return user.is_staff or user.groups.filter(name="POLE_FINANCIER").exists()

def has_administratif_access(user):
    """
    Renvoie vrai si un utilisateur peut accéder au pôle administratif

    Args:
        user (User):  L'utilisateur
    """
    user = User.objects.get(username=user.username)
    return user.is_superuser or user.is_staff or user.groups.filter(name="POLE_ADMINISTRATIF").exists()

def has_technique_access(user):
    """
    Renvoie vrai si un utilisateur peut accéder au pôle technique

    Args:
        user (User):  L'utilisateur
    """
    user = User.objects.get(username=user.username)
    return user.is_superuser or user.is_staff or user.groups.filter(name="POLE_TECHNIQUE").exists()

def has_ceo_access(user):
    """
    Renvoie vrai si un utilisateur a les accès du CEO

    Args:
        user (User):  L'utilisateur
    """
    user = User.objects.get(username=user.username)
    return user.groups.filter(name="CEO").exists()

def has_collaborateur_access(user):
    """
    Renvoie vrai si un utilisateur a les accès des collaborateurs

    Args:
        user (User):  L'utilisateur
    """
    user = User.objects.get(username=user.username)
    return not (user.is_superuser or user.is_staff) and user.groups.filter(name="COLLABORATEUR").exists()

def can_read_facture(user):
    """
    Renvoie vrai si un utilisateur peut voir des factures

    Args:
        user (User):  L'utilisateur
    """
    user = User.objects.get(username=user.username)
    if has_finance_access(user) or has_collaborateur_access(user):
        return True
    else:
        return False