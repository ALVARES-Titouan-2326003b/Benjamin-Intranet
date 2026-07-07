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
        or user.groups.filter(name="POLE_PROMOTION").exists()
        or user.groups.filter(name="POLE_DEVELOPPEMENT").exists()
        or user.groups.filter(name="POLE_INVESTISSEMENT").exists()
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
    return getattr(user, "is_authenticated", False)


def can_create_facture(user):
    """
    Renvoie vrai si un utilisateur peut créer des factures
    Tout utilisateur connecté peut transmettre une facture.

    Args:
        user (User):  L'utilisateur
    """
    return getattr(user, "is_authenticated", False)


def can_change_facture_status(user):
    """
    Renvoie vrai si un utilisateur peut modifier le statut d'une facture.
    Le statut est réservé au pôle financier, indépendamment du rôle collaborateur.
    """
    if not getattr(user, "is_authenticated", False):
        return False
    user = User.objects.get(username=user.username)
    return user.groups.filter(name="POLE_FINANCIER").exists()


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
    if getattr(user, "is_authenticated", False):
        return (
            facture.collaborateur_id == user.id
            or facture.created_by_id == user.id
            or facture.demandeur_id == user.id
        )
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
        if field == 'statut':
            return can_change_facture_status(user)
        return True
    
    # Les demandeurs ne peuvent éditer que leurs propres factures
    # et seulement certains champs.
    if getattr(user, "is_authenticated", False) and (
        facture.collaborateur_id == user.id
        or facture.created_by_id == user.id
        or facture.demandeur_id == user.id
    ):
        # Ces champs ne peuvent pas être édités par les collaborateurs
        forbidden_fields = ['collaborateur']
        if not can_change_facture_status(user):
            forbidden_fields.append('statut')
        return field not in forbidden_fields
    
    return False
