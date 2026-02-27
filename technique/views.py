import json
from reportlab.lib import colors
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse
from .services.documents import extract_text_from_file
from .services.ai_summary import summarize_document
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from .models import DocumentTechnique, TechnicalProject
from .forms import (
    DocumentTechniqueUploadForm,
    TechnicalProjectCreateForm,
    TechnicalProjectFinanceForm,
)
from user_access.user_test_functions import has_technique_access


@login_required
@user_passes_test(has_technique_access, login_url="/", redirect_field_name=None)
def documents_list(request):
    """
    Affiche la liste des documents techniques
    """
    qs = DocumentTechnique.objects.all()
    projet = request.GET.get("projet", "").strip()
    if projet:
        qs = qs.filter(projet__icontains=projet)

    return render(
        request,
        "technique/documents_list.html",
        {
            "documents": qs,
            "projet": projet,
        },
    )


@login_required
@user_passes_test(has_technique_access, login_url="/", redirect_field_name=None)
def documents_upload(request):
    """
    Affiche une vue pour enregistrer un document
    """
    if request.method == "POST":
        form = DocumentTechniqueUploadForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            if request.user.is_authenticated:
                obj.created_by = request.user

            # Extraction du texte
            fileobj = obj.fichier
            texte = extract_text_from_file(fileobj) or ""

            if not texte.strip():
                messages.error(
                    request,
                    "Impossible d'extraire du texte du document "
                )
                return render(
                    request,
                    "technique/documents_upload.html",
                    {"form": form},
                )

            obj.texte_brut = texte[:500000]

            # Résumé IA
            """
            meta = {
                "projet": obj.projet,
                "titre": obj.titre,
                "type_document": obj.get_type_document_display(),
            }
            """
            summary = summarize_document(obj.texte_brut)

            obj.resume = (summary.get("resume") or "")[:50000]
            obj.prix = (summary.get("prix") or "")[:20000]
            obj.dates = (summary.get("dates") or "")[:20000]
            obj.conditions_suspensives = (summary.get("conditions_suspensives") or "")[
                :20000
            ]
            obj.penalites = (summary.get("penalites") or "")[:20000]
            obj.delais = (summary.get("delais") or "")[:20000]
            obj.clauses_importantes = json.dumps((summary.get("clauses_importantes") or [])[:50000])

            obj.save()

            messages.success(
                request,
                "Document importé et résumé avec succès.",
            )
            return redirect("technique:documents_detail", pk=obj.pk)
    else:
        form = DocumentTechniqueUploadForm()

    return render(request, "technique/documents_upload.html", {"form": form})


@login_required
@user_passes_test(has_technique_access, login_url="/", redirect_field_name=None)
def documents_detail(request, pk):
    """
    Affiche les informations d'un docment technique

    Args:
        request (HTTPRequest): Requête HTTP
        pk (int): Identifiant du document
    """
    doc = get_object_or_404(DocumentTechnique, pk=pk)
    return render(
        request,
        "technique/documents_detail.html",
        {
            "document": doc,
        },
    )


@login_required
@user_passes_test(has_technique_access, login_url="/", redirect_field_name=None)
def document_resume_pdf(request, pk):
    """
    Génère un PDF simple avec le résumé et les sections structurées.

    Args:
        request (HTTPRequest): Requête HTTP
        pk (int): Identifiant du document
    """

    doc = get_object_or_404(DocumentTechnique, pk=pk)

    response = HttpResponse(content_type="application/pdf")
    filename = f"resume_{doc.pk}.pdf"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    x_margin = 2 * cm
    y = height - 2 * cm
    max_line_width = width - 2 * x_margin  # Redimensionne sinon dépasse la page

    def wrap_text(text: str, font: str = "Helvetica", size: int = 10):
        #Permet de découper le texte
        lines_out = []
        if not text:
            return lines_out

        p.setFont(font, size)

        for raw_line in str(text).split("\n"):
            line = raw_line.rstrip()
            if not line:
                lines_out.append("")
                continue

            words = line.split(" ")
            current = ""

            for w in words:
                candidate = (current + " " + w).strip()
                w_width = pdfmetrics.stringWidth(candidate, font, size)
                if w_width <= max_line_width:
                    current = candidate
                else:
                    if current:
                        lines_out.append(current)
                    current = w
            if current:
                lines_out.append(current)

        return lines_out

    def find_all_occurrences(text: str, sub: str):
        start = 0
        while True:
            idx = text.find(sub, start)
            if idx == -1:
                break
            yield idx
            start = idx + len(sub)

    def write_line(text, font="Helvetica", size=10, leading=14, highlight_clauses=None):
        #Eviter les lignes vides et aussi les espaces inutiles
        nonlocal y
        if not text:
            return

        lines = wrap_text(text, font=font, size=size)
        p.setFont(font, size)

        for line in lines:
            if not line.strip():
                continue

            if y < 2 * cm:
                p.showPage()
                y = height - 2 * cm
                p.setFont(font, size)

            # Surligne
            if highlight_clauses:
                for clause in highlight_clauses:
                    if not clause:
                        continue

                    for idx in find_all_occurrences(line, clause):
                        prefix = line[:idx]
                        text_before_width = pdfmetrics.stringWidth(prefix, font, size)
                        clause_width = pdfmetrics.stringWidth(clause, font, size)

                        p.setFillColor(colors.yellow)
                        p.rect(
                            x_margin + text_before_width - 1,
                            y - 2,
                            clause_width + 2,
                            leading,
                            fill=1,
                            stroke=0,
                        )
                        p.setFillColor(colors.black)

            # Texte
            p.drawString(x_margin, y, line)
            y -= leading

    # Titre
    p.setFont("Helvetica-Bold", 14)
    p.drawString(x_margin, y, "Résumé du document")
    y -= 20

    write_line(f"Titre : {doc.titre}", size=11)
    write_line(f"Projet : {doc.projet or '—'}", size=11)
    write_line(f"Type : {doc.get_type_document_display()}", size=11)
    y -= 10 

    # Sections – si aucune donnée : "—"
    def section(titre, contenu, highlight=False):
        nonlocal y
        contenu = (contenu or "").strip()
        if not contenu or contenu == "—":
            return
        # Titre de section
        if y < 2 * cm:
            p.showPage()
            y = height - 2 * cm

        p.setFont("Helvetica-Bold", 12)
        p.drawString(x_margin, y, titre)
        y -= 16
        # Contenu
        write_line(contenu, highlight_clauses=json.loads(doc.clauses_importantes or "[]") if highlight else None)
        y -= 4

    section("Résumé global", doc.resume, highlight=True)
    section("Prix / montants", doc.prix)
    section("Dates clés", doc.dates)
    section("Conditions suspensives", doc.conditions_suspensives)
    section("Pénalités", doc.penalites)
    section("Délais", doc.delais)

    p.showPage()
    p.save()
    return response





@login_required
@user_passes_test(has_technique_access, login_url="/", redirect_field_name=None)
def financial_overview(request):
    """
    Affiche la liste des projets techniques
    """
    projects = TechnicalProject.objects.all().order_by("name")

    if request.method == "POST":
        form = TechnicalProjectCreateForm(request.POST)
        if form.is_valid():
            #project = form.save()
            messages.success(request, "Projet créé avec succès.")
            return redirect("technique_financial_overview")
    else:
        form = TechnicalProjectCreateForm()

    return render(
        request,
        "technique/vue_financiere_list.html",
        {"projects": projects, "form": form},
    )


@login_required
@user_passes_test(has_technique_access, login_url="/", redirect_field_name=None)
def financial_project_detail(request, pk):
    """
    Saisie des données financières + graphiques

    Args:
        request (HttpRequest): Requête HTTP
        pk (str): Identifiant du projet
    """
    project = get_object_or_404(TechnicalProject, pk=pk)

    if request.method == "POST":
        form = TechnicalProjectFinanceForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, "Données financières mises à jour.")
            return redirect("technique_financial_project_detail", pk=project.pk)
    else:
        form = TechnicalProjectFinanceForm(instance=project)

    context = {
        "project": project,
        "form": form,
        "frais_engages": project.frais_engages,
        "frais_payes": project.frais_payes,
        "frais_restants": project.frais_restants,
        "total_estime": project.total_estimated,
    }
    return render(request, "technique/vue_financiere.html", context)


@login_required
@user_passes_test(has_technique_access, login_url="/", redirect_field_name=None)
def financial_project_pdf(request, pk):
    """
    Permet de télécharger le PDF de la vue financière

    Args:
        request (HttpRequest): Requête HTTP
        pk (str): Identifiant du projet
    """
    project = get_object_or_404(TechnicalProject, pk=pk)

    response = HttpResponse(content_type="application/pdf")
    filename = f"vue_financiere_{project.reference}.pdf"
    response["Content-Disposition"] = f'attachment; filename=\"{filename}\"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    x_margin = 2 * cm
    y = height - 2 * cm
    max_line_width = width - 2 * x_margin

    def wrap_text(text: str, font: str = "Helvetica", size: int = 10):
        lines_out = []
        if not text:
            return lines_out

        p.setFont(font, size)

        for raw_line in str(text).split("\n"):
            line = raw_line.rstrip()
            if not line:
                lines_out.append("")
                continue

            words = line.split(" ")
            current = ""

            for w in words:
                candidate = (current + " " + w).strip()
                w_width = pdfmetrics.stringWidth(candidate, font, size)
                if w_width <= max_line_width:
                    current = candidate
                else:
                    if current:
                        lines_out.append(current)
                    current = w
            if current:
                lines_out.append(current)

        return lines_out

    def write_line(text, font="Helvetica", size=10, leading=14):
        nonlocal y
        if text is None:
            return

        lines = wrap_text(str(text), font=font, size=size)

        for line in lines:
            if not line.strip():
                continue
            if y < 2 * cm:
                p.showPage()
                y = height - 2 * cm
                p.setFont(font, size)
            p.setFont(font, size)
            p.drawString(x_margin, y, line)
            y -= leading

    # Titre
    p.setFont("Helvetica-Bold", 14)
    p.drawString(x_margin, y, "Vue financière projetée")
    y -= 20

    write_line(f"Projet : {project.name} ({project.reference})", size=11)
    y -= 10

    write_line(f"Frais engagés : {project.frais_engages} €", size=11)
    write_line(f"Frais déjà payés : {project.frais_payes} €", size=11)
    write_line(f"Frais restants à régler : {project.frais_restants} €", size=11)
    write_line(f"Total estimé du projet : {project.total_estimated} €", size=11)
    write_line(f"Reste à engager : {project.reste_a_engager} €", size=11)

    p.showPage()
    p.save()
    return response


# ================== Suppression en masse ==================

@login_required
@user_passes_test(has_technique_access, login_url="/", redirect_field_name=None)
def bulk_delete_projects(request):
    """
    Vue pour supprimer plusieurs projets techniques en une seule action
    """
    if request.method != "POST":
        return redirect("technique_financial_overview")
    
    project_ids = request.POST.getlist('project_ids')
    
    if not project_ids:
        messages.warning(request, "Aucun projet sélectionné.")
        return redirect("technique_financial_overview")
    
    try:
        deleted_count = TechnicalProject.objects.filter(id__in=project_ids).delete()[0]
        messages.success(
            request,
            f"✅ {deleted_count} projet{'s' if deleted_count > 1 else ''} supprimé{'s' if deleted_count > 1 else ''} avec succès."
        )
    except Exception as e:
        messages.error(request, f"❌ Erreur lors de la suppression : {str(e)}")
    
    return redirect("technique_financial_overview")


@login_required
@user_passes_test(has_technique_access, login_url="/", redirect_field_name=None)
def bulk_delete_documents(request):
    """
    Vue pour supprimer plusieurs documents techniques en une seule action
    """
    if request.method != "POST":
        return redirect("technique:documents_list")
    
    document_ids = request.POST.getlist('document_ids')
    
    if not document_ids:
        messages.warning(request, "Aucun document sélectionné.")
        return redirect("technique:documents_list")
    
    try:
        deleted_count = DocumentTechnique.objects.filter(id__in=document_ids).delete()[0]
        messages.success(
            request,
            f"✅ {deleted_count} document{'s' if deleted_count > 1 else ''} supprimé{'s' if deleted_count > 1 else ''} avec succès."
        )
    except Exception as e:
        messages.error(request, f"❌ Erreur lors de la suppression : {str(e)}")
    
    return redirect("technique:documents_list")


