from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import FicheDePoste, Candidature
from .forms import FicheDePosteForm, CVUploadForm
from .services.parsing import extract_text
from .services.ai import score_cv
from user_access.user_test_functions import has_finance_access

@login_required
@user_passes_test(has_finance_access, login_url="/", redirect_field_name=None)
def dashboard(request):
    fiches = FicheDePoste.objects.order_by("-created_at")
    recents = Candidature.objects.select_related("fiche", "candidat")[:20]
    return render(request, "recrutement/dashboard.html", {
        "fiches": fiches,
        "candidatures": recents,
    })

@login_required
@user_passes_test(has_finance_access, login_url="/", redirect_field_name=None)
def fiche_create(request):
    if request.method == "POST":
        form = FicheDePosteForm(request.POST)
        if form.is_valid():
            fiche = form.save(commit=False)
            fiche.created_by = request.user if request.user.is_authenticated else None
            fiche.save()
            messages.success(request, "Fiche de poste créée.")
            return redirect("recrutement:fiche_detail", pk=fiche.pk)
    else:
        form = FicheDePosteForm()
    return render(request, "recrutement/job_form.html", {"form": form})

@login_required
@user_passes_test(has_finance_access, login_url="/", redirect_field_name=None)
def fiche_detail(request, pk):
    fiche = get_object_or_404(FicheDePoste, pk=pk)
    upload_form = CVUploadForm()
    candidatures = fiche.candidatures.select_related("candidat")
    return render(request, "recrutement/job_detail.html", {
        "fiche": fiche,
        "upload_form": upload_form,
        "candidatures": candidatures,
    })

@login_required
@user_passes_test(has_finance_access, login_url="/", redirect_field_name=None)
def upload_cv(request, pk):
    fiche = get_object_or_404(FicheDePoste, pk=pk)
    if request.method != "POST":
        return redirect("recrutement:fiche_detail", pk=pk)

    form = CVUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(request, "Formulaire invalide.")
        return redirect("recrutement:fiche_detail", pk=pk)

    candidat = form.save(commit=False)
    # Extraire du texte
    text = extract_text(candidat.cv_fichier) or ""

    # Si on arrive pas à extraire on n'enregistre pas
    if not text.strip():
        messages.error(
            request,
            f"Impossible de lire le contenu du fichier « {candidat.cv_fichier.name} ». "
            "Le CV semble être vide ou non lisible. Rien n’a été enregistré."
        )
        return redirect("recrutement:fiche_detail", pk=pk)

    candidat.cv_texte = text[:200000] 
    candidat.save()

    # Créer la candidature
    cand, _ = Candidature.objects.get_or_create(fiche=fiche, candidat=candidat)

    # Construire le texte de job
    job_text = f"{fiche.titre}\n\n{fiche.description}\n\nCompétences clés: {fiche.competences_clees}"
    res = score_cv(job_text, candidat.cv_texte)

    cand.score = res.get("score")
    cand.explication = res.get("explication", "")[:2000]
    cand.save()

    messages.success(request, f"CV déposé. Score: {cand.score if cand.score is not None else '—'}")
    return redirect("recrutement:fiche_detail", pk=pk)


# ================== Suppression en masse ==================

@login_required
@user_passes_test(has_finance_access, login_url="/", redirect_field_name=None)
def bulk_delete_fiches(request):
    """
    Vue pour supprimer plusieurs fiches de poste en une seule action
    """
    if request.method != "POST":
        return redirect("recrutement:dashboard")
    
    fiche_ids = request.POST.getlist('fiche_ids')
    
    if not fiche_ids:
        messages.warning(request, "Aucune fiche sélectionnée.")
        return redirect("recrutement:dashboard")
    
    try:
        deleted_count = FicheDePoste.objects.filter(id__in=fiche_ids).delete()[0]
        messages.success(
            request,
            f"✅ {deleted_count} fiche{'s' if deleted_count > 1 else ''} supprimée{'s' if deleted_count > 1 else ''} avec succès."
        )
    except Exception as e:
        messages.error(request, f"❌ Erreur lors de la suppression : {str(e)}")
    
    return redirect("recrutement:dashboard")


@login_required
@user_passes_test(has_finance_access, login_url="/", redirect_field_name=None)
def bulk_delete_candidatures(request):
    """
    Vue pour supprimer plusieurs candidatures en une seule action
    """
    if request.method != "POST":
        return redirect("recrutement:dashboard")
    
    candidature_ids = request.POST.getlist('candidature_ids')
    
    if not candidature_ids:
        messages.warning(request, "Aucune candidature sélectionnée.")
        return redirect("recrutement:dashboard")
    
    try:
        deleted_count = Candidature.objects.filter(id__in=candidature_ids).delete()[0]
        messages.success(
            request,
            f"✅ {deleted_count} candidature{'s' if deleted_count > 1 else ''} supprimée{'s' if deleted_count > 1 else ''} avec succès."
        )
    except Exception as e:
        messages.error(request, f"❌ Erreur lors de la suppression : {str(e)}")
    
    return redirect("recrutement:dashboard")

  