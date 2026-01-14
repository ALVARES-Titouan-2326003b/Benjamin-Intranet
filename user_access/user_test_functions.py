from django.contrib.auth.models import User


def has_finance_access(user):
    user = User.objects.get(username=user.username)
    return user.is_staff or user.groups.filter(name="POLE_FINANCIER").exists()

def has_administratif_access(user):
    user = User.objects.get(username=user.username)
    return user.is_superuser or user.is_staff or user.groups.filter(name="POLE_ADMINISTRATIF").exists()

def has_technique_access(user):
    user = User.objects.get(username=user.username)
    return user.is_superuser or user.is_staff or user.groups.filter(name="POLE_TECHNIQUE").exists()

def has_ceo_access(user):
    user = User.objects.get(username=user.username)
    return user.is_superuser or user.is_staff or user.groups.filter(name="CEO").exists()

def has_collaborateur_access(user):
    user = User.objects.get(username=user.username)
    return not (user.is_superuser or user.is_staff) and user.groups.filter(name="COLLABORATEUR").exists()

def can_read_facture(user):
    user = User.objects.get(username=user.username)
    if has_finance_access(user) or has_collaborateur_access(user):
        return True
    else:
        return False