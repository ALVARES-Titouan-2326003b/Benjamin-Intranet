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
        user (User) :  L'utilisateur
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


def has_all_poles_access(user):
    """
    Renvoie vrai si un utilisateur a accès à au moins un des pôles gérés (CEO, financier, administratif, technique).

    Args:
        user (User):  L'utilisateur
    """
    user = User.objects.get(username=user.username)

    if user.is_superuser or user.is_staff:
        return True

    return (
        user.groups.filter(name="CEO").exists()
        or user.groups.filter(name="POLE_FINANCIER").exists()
        or user.groups.filter(name="POLE_ADMINISTRATIF").exists()
        or user.groups.filter(name="POLE_TECHNIQUE").exists()
    )


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
    if has_finance_access(user) or has_ceo_access(user) or has_collaborateur_access(user):
        return True
    else:
        return False


def can_create_facture(user):
    """
    Renvoie vrai si un utilisateur peut créer des factures
    Les collaborateurs et le finance peuvent créer des factures

    Args:
        user (User):  L'utilisateur
    """
    user = User.objects.get(username=user.username)
    return has_finance_access(user) or has_collaborateur_access(user)


def is_facture_creator(user, facture):
    """
    Vérifie si l'utilisateur a créé la facture

    Args:
        user (User):  L'utilisateur
        facture (Facture):  La facture
    """
    return facture.created_by_id == user.id


def can_edit_facture(user, facture):
    """
    Vérifie si l'utilisateur peut éditer la facture
    - Finance: peut éditer toutes les factures
    - Collaborateurs: peuvent éditer seulement leurs propres factures

    Args:
        user (User):  L'utilisateur
        facture (Facture):  La facture
    """
    user = User.objects.get(username=user.username)
    if has_finance_access(user):
        return True
    if has_collaborateur_access(user):
        return facture.collaborateur_id == user.id
    return False


def can_edit_facture_field(user, facture, field):
    """
    Vérifie si l'utilisateur peut éditer un champ spécifique de la facture
    - Finance: peut éditer tous les champs
    - Collaborateurs: peuvent éditer tous les champs SAUF 'statut' et 'collaborateur'

    Args:
        user (User):  L'utilisateur
        facture (Facture):  La facture
        field (str):  Le nom du champ
    """
    user = User.objects.get(username=user.username)
    
    # Finance peut éditer tous les champs
    if has_finance_access(user):
        return True
    
    # Collaborateurs ne peuvent éditer que s'ils sont les créateurs
    # et seulement certains champs
    if has_collaborateur_access(user) and facture.collaborateur_id == user.id:
        # Ces champs ne peuvent pas être édités par les collaborateurs
        forbidden_fields = ['statut', 'collaborateur']
        return field not in forbidden_fields
    
    return False
