"""
Context processors pour rendre des variables disponibles dans tous les templates
"""

def user_role_context(request):
    """
    Ajoute is_only_collaborator au contexte de tous les templates
    """
    if request.user.is_authenticated:
        # Vérifie si l'utilisateur est uniquement collaborateur
        if request.user.is_superuser or request.user.is_staff:
            is_only_collaborator = False
        else:
            user_groups = set(request.user.groups.values_list('name', flat=True))
            is_only_collaborator = not user_groups or user_groups == {'COLLABORATEUR'}
    else:
        is_only_collaborator = False
    
    return {
        'is_only_collaborator': is_only_collaborator
    }
