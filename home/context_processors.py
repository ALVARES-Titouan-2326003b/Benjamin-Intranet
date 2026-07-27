"""
Context processors pour rendre des variables disponibles dans tous les templates
"""

def user_role_context(request):
    """
    Ajoute les rôles de navigation au contexte de tous les templates.
    """
    if request.user.is_authenticated:
        user_groups = set(request.user.groups.values_list('name', flat=True))
        is_ceo = request.user.is_superuser or "CEO" in user_groups
        is_only_collaborator = (
            not request.user.is_superuser
            and not request.user.is_staff
            and (not user_groups or user_groups == {"COLLABORATEUR"})
        )
        can_finance = is_ceo or "POLE_FINANCIER" in user_groups
        can_manage_technique = is_ceo or "POLE_TECHNIQUE" in user_groups
        can_administratif = is_ceo or "POLE_ADMINISTRATIF" in user_groups
        can_view_technical_dossiers = can_manage_technique or can_administratif
        can_signatures = bool(
            request.user.is_superuser
            or request.user.is_staff
            or user_groups.intersection(
                {
                    "CEO",
                    "POLE_FINANCIER",
                    "POLE_TECHNIQUE",
                    "POLE_ADMINISTRATIF",
                    "POLE_PROMOTION",
                    "POLE_DEVELOPPEMENT",
                    "POLE_INVESTISSEMENT",
                }
            )
        )
    else:
        is_only_collaborator = False
        is_ceo = False
        can_finance = False
        can_manage_technique = False
        can_administratif = False
        can_view_technical_dossiers = False
        can_signatures = False

    return {
        "is_only_collaborator": is_only_collaborator,
        "nav_is_ceo": is_ceo,
        "nav_can_finance": can_finance,
        "nav_can_manage_technique": can_manage_technique,
        "nav_can_administratif": can_administratif,
        "nav_can_view_technical_dossiers": can_view_technical_dossiers,
        "nav_can_signatures": can_signatures,
    }
