from django.shortcuts import render
from django.db.models import Q
from django.contrib.auth.decorators import login_required

from invoices.models import Facture
from signatures.models import Document
from recrutement.models import Candidat
from technique.models import TechnicalProject, DocumentTechnique
from user_access.user_test_functions import (has_administratif_access,
                                             has_finance_access,
                                             has_technique_access,
                                             has_collaborateur_access)

def is_only_collaborator(user):
    """
    Retourne True si l'utilisateur est UNIQUEMENT collaborateur
    (pas superuser, pas staff, et n'a que le groupe COLLABORATEUR ou aucun groupe)
    """
    if user.is_superuser or user.is_staff:
        return False
    
    # Récupère tous les groupes de l'utilisateur
    user_groups = set(user.groups.values_list('name', flat=True))
    
    # Si pas de groupe ou seulement COLLABORATEUR
    if not user_groups or user_groups == {'COLLABORATEUR'}:
        return True
    
    return False

@login_required
def dashboard_view(request):
    """
    Affiche un tableau de bord avec différents pôles selon les accès de l'utilisateur.
    """
    return render(request, 'home_dashboard.html', {
        'access_finance': has_finance_access(request.user),
        'access_technique': has_technique_access(request.user),
        'access_administratif': has_administratif_access(request.user),
        'access_collaborator': has_collaborateur_access(request.user),
        'is_only_collaborator': is_only_collaborator(request.user)
    })

@login_required
def global_search(request):
    """
    Affiche les résultats de la recherche globale.
    """
    query = request.GET.get('q', '').strip()
    context = {'query': query}

    if query:
        if has_finance_access(request.user):
            # 1. Factures (ID, Titre, Client, Fournisseur)
            factures = Facture.objects.filter(
                Q(id__icontains=query) |
                Q(titre__icontains=query) |
                Q(fournisseur__icontains=query) |
                Q(client__nom__icontains=query)
            )[:10]
        else:
            factures = []
        if has_finance_access(request.user):
            # 2. Documents (Signatures) (Titre)
            documents = Document.objects.filter(
                titre__icontains=query
            )[:10]

            # 3. Candidats (Nom, Email)
            candidats = Candidat.objects.filter(
                Q(nom__icontains=query) |
                Q(email__icontains=query)
            )[:10]
        else:
            documents = []
            candidats = []

        if has_technique_access(request.user):
            # 4. Projets Techniques (Nom, Reference)
            projets = TechnicalProject.objects.filter(
                Q(name__icontains=query) |
                Q(reference__icontains=query)
            )[:10]

            # 5. Documents Techniques (Titre, Projet)
            docs_tech = DocumentTechnique.objects.filter(
                 Q(titre__icontains=query) |
                 Q(projet__icontains=query)
            )[:10]
        else :
            projets = []
            docs_tech = []

        context.update({
            'factures': factures,
            'documents': documents,
            'candidats': candidats,
            'projets': projets,
            'docs_tech': docs_tech,
            'results_count': len(factures) + len(documents) + len(candidats) + len(projets) + len(docs_tech)
        })

    return render(request, 'home/search_results.html', context)
