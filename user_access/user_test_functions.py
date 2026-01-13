from django.contrib.auth.models import User


def has_finance_access(user):
    user = User.objects.get(username=user.username)
    return user.groups.filter(name="POLE_FINANCIER").exists()

def has_administratif_access(user):
    user = User.objects.get(username=user.username)
    return user.groups.filter(name="POLE_ADMINISTRATIF").exists()

def has_technique_access(user):
    user = User.objects.get(username=user.username)
    return user.groups.filter(name="POLE_TECHNIQUE").exists()

def is_ceo(user):
    user = User.objects.get(username=user.username)
    return user.groups.filter(name="CEO").exists()

def is_collaborateur(user):
    user = User.objects.get(username=user.username)
    return user.groups.filter(name="COLLABORATEUR").exists()

def can_read_facture(user):
    user = User.objects.get(username=user.username)
    if has_finance_access(user) or is_collaborateur(user):
        return True
    else:
        return False