from django.shortcuts import render
from django.db.models import Q
from django.contrib.auth.decorators import login_required

from invoices.models import Facture
from signatures.models import Document
from recrutement.models import Candidat
from technique.models import TechnicalProject, DocumentTechnique

@login_required
def dashboard_view(request):
    return render(request, 'home_dashboard.html')

@login_required
def global_search(request):
    query = request.GET.get('q', '').strip()
    context = {'query': query}

    if query:
        # 1. Factures (ID, Titre, Client, Fournisseur)
        factures = Facture.objects.filter(
            Q(id__icontains=query) |
            Q(titre__icontains=query) |
            Q(fournisseur__icontains=query) |
            Q(client__nom__icontains=query)
        )[:10]

        # 2. Documents (Signatures) (Titre)
        documents = Document.objects.filter(
            titre__icontains=query
        )[:10]

        # 3. Candidats (Nom, Email)
        candidats = Candidat.objects.filter(
            Q(nom__icontains=query) |
            Q(email__icontains=query)
        )[:10]

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

        context.update({
            'factures': factures,
            'documents': documents,
            'candidats': candidats,
            'projets': projets,
            'docs_tech': docs_tech,
            'results_count': len(factures) + len(documents) + len(candidats) + len(projets) + len(docs_tech)
        })

    return render(request, 'home/search_results.html', context)
