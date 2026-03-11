import json, csv
from reportlab.lib import colors
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from openpyxl import Workbook
from .services.documents import extract_text_from_file
from .services.ai_summary import summarize_document
from .models import DocumentTechnique, TechnicalProject, ProjectExpense
from .forms import (
    DocumentTechniqueUploadForm,
    TechnicalProjectCreateForm,
    TechnicalProjectFinanceForm,
    DocumentTechniqueUpdateForm,
    ProjectExpenseForm,
)
from user_access.user_test_functions import has_technique_access
from django.shortcuts import get_object_or_404
from django.db.models import Q

@login_required
@user_passes_test(has_technique_access, login_url="/", redirect_field_name=None)
def documents_list(request):
    """
    Affiche la liste des documents techniques
    avec recherche et filtres.
    """
    qs = DocumentTechnique.objects.all()

    q = (request.GET.get("q") or "").strip()
    projet = (request.GET.get("projet") or "").strip()
    type_document = (request.GET.get("type_document") or "").strip()
    sort = (request.GET.get("sort") or "").strip()

    if q:
        qs = qs.filter(
            Q(titre__icontains=q)
            | Q(projet__icontains=q)
            | Q(resume__icontains=q)
            | Q(prix__icontains=q)
            | Q(dates__icontains=q)
            | Q(conditions_suspensives__icontains=q)
            | Q(penalites__icontains=q)
            | Q(delais__icontains=q)
            | Q(clauses_importantes__icontains=q)
        )

    if projet:
        qs = qs.filter(projet__icontains=projet)

    if type_document:
        qs = qs.filter(type_document=type_document)

    if sort == "oldest":
        qs = qs.order_by("created_at")
    else:
        qs = qs.order_by("-created_at")

    return render(
        request,
        "technique/documents_list.html",
        {
            "documents": qs,
            "q": q,
            "projet": projet,
            "type_document": type_document,
            "sort": sort,
            "type_choices": DocumentTechnique.TYPE_CHOICES,
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

            texte = extract_text_from_file(obj.fichier) or ""

            if not texte.strip():
                messages.error(request, "Impossible d'extraire du texte du document.")
                return render(request, "technique/documents_upload.html", {"form": form})

            obj.texte_brut = texte[:500000]
            summary = summarize_document(obj.texte_brut)

            obj.resume = (summary.get("resume") or "")[:50000]
            obj.prix = (summary.get("prix") or "")[:20000]
            obj.dates = (summary.get("dates") or "")[:20000]
            obj.conditions_suspensives = (summary.get("conditions_suspensives") or "")[:20000]
            obj.penalites = (summary.get("penalites") or "")[:20000]
            obj.delais = (summary.get("delais") or "")[:20000]
            obj.clauses_importantes = json.dumps((summary.get("clauses_importantes") or [])[:50000])

            obj.save()
            messages.success(request, "Document importé et résumé avec succès.")
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
    return render(request, "technique/documents_detail.html", {"document": doc})


@login_required
@user_passes_test(has_technique_access, login_url="/", redirect_field_name=None)
def documents_update(request, pk):
    document = get_object_or_404(DocumentTechnique, pk=pk)

    if request.method == "POST":
        form = DocumentTechniqueUpdateForm(request.POST, instance=document)
        if form.is_valid():
            form.save()
            messages.success(request, "Document modifié avec succès.")
            return redirect("technique:documents_detail", pk=document.pk)
    else:
        form = DocumentTechniqueUpdateForm(instance=document)

    return render(
        request,
        "technique/documents_update.html",
        {"form": form, "document": document},
    )

@login_required
@user_passes_test(has_technique_access, login_url="/", redirect_field_name=None)
def document_resume_pdf(request, pk):
    """
    Génère un PDF simple avec le résumé et les sections structurées.

    Args:
        request (HTTPRequest) : Requête HTTP
        pk (int) : Identifiant du document
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
def documents_update(request, pk):
    document = get_object_or_404(DocumentTechnique, pk=pk)

    if request.method == "POST":
        form = DocumentTechniqueUpdateForm(
            request.POST,
            instance=document
        )

        if form.is_valid():
            form.save()
            messages.success(request, "Document modifié avec succès.")
            return redirect("technique:documents_detail", pk=document.pk)

    else:
        form = DocumentTechniqueUpdateForm(instance=document)

    return render(
        request,
        "technique/documents_update.html",
        {
            "form": form,
            "document": document,
        },
    )


@login_required
@user_passes_test(has_technique_access, login_url="/", redirect_field_name=None)
def financial_overview(request):
    """
    Affiche la liste des projets techniques
    avec recherche et filtres.
    """
    projects = TechnicalProject.objects.all()

    q = (request.GET.get("q") or "").strip()
    reference = (request.GET.get("reference") or "").strip()
    project_type = (request.GET.get("type") or "").strip()
    sort = (request.GET.get("sort") or "").strip()

    if q:
        projects = projects.filter(
            Q(name__icontains=q) | Q(reference__icontains=q)
        )

    if reference:
        projects = projects.filter(reference__icontains=reference)

    if project_type:
        projects = projects.filter(type=project_type)

    if sort == "name_desc":
        projects = projects.order_by("-name")
    elif sort == "ref_asc":
        projects = projects.order_by("reference")
    elif sort == "ref_desc":
        projects = projects.order_by("-reference")
    else:
        projects = projects.order_by("name")

    # PAGINATION
    paginator = Paginator(projects, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    if request.method == "POST":
        form = TechnicalProjectCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Projet créé avec succès.")
            return redirect("technique:technique_financial_overview")
    else:
        form = TechnicalProjectCreateForm()

    return render(
        request,
        "technique/vue_financiere_list.html",
        {
            "projects": page_obj,
            "page_obj": page_obj,
            "form": form,
            "q": q,
            "reference": reference,
            "selected_type": project_type,
            "sort": sort,
            "type_choices": TechnicalProject.DOSSIER_TYPES,
        },
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
    project.refresh_amounts_from_expenses()

    if request.method == "POST" and "total_estimated" in request.POST:
        form = TechnicalProjectFinanceForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, "Budget prévisionnel mis à jour.")
            return redirect("technique:technique_financial_project_detail", pk=project.pk)
    else:
        form = TechnicalProjectFinanceForm(instance=project)

    expense_q = (request.GET.get("expense_q") or "").strip()
    expense_status = (request.GET.get("expense_status") or "").strip()

    expenses = project.expenses.all().order_by("-due_date", "-id")

    if expense_q:
        expenses = expenses.filter(label__icontains=expense_q)

    if expense_status == "paid":
        expenses = expenses.filter(is_paid=True)
    elif expense_status == "unpaid":
        expenses = expenses.filter(is_paid=False)

    expense_form = ProjectExpenseForm()

    budget_ratio = 0
    if project.total_estimated and project.total_estimated > 0:
        budget_ratio = (project.frais_engages / project.total_estimated) * 100

    if project.frais_engages > project.total_estimated:
        budget_status = "over"
        budget_label = "Dépassé"
    elif budget_ratio >= 80:
        budget_status = "warning"
        budget_label = "À surveiller"
    else:
        budget_status = "ok"
        budget_label = "OK"

    return render(
        request,
        "technique/vue_financiere.html",
        {
            "project": project,
            "form": form,
            "expense_form": expense_form,
            "expenses": expenses,
            "expense_q": expense_q,
            "expense_status": expense_status,
            "frais_engages": project.frais_engages,
            "frais_payes": project.frais_payes,
            "frais_restants": project.frais_restants,
            "reste_a_engager": project.reste_a_engager,
            "total_estime": project.total_estimated,
            "budget_status": budget_status,
            "budget_label": budget_label,
            "budget_ratio": round(budget_ratio, 2),
        },
    )

@login_required
@user_passes_test(has_technique_access, login_url="/", redirect_field_name=None)
def project_expense_create(request, pk):
    project = get_object_or_404(TechnicalProject, pk=pk)

    if request.method == "POST":
        form = ProjectExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.project = project
            expense.save()
            messages.success(request, "Dépense ajoutée avec succès.")
        else:
            messages.error(request, "Impossible d'ajouter la dépense.")
    return redirect("technique:technique_financial_project_detail", pk=project.pk)



@login_required
@user_passes_test(has_technique_access, login_url="/", redirect_field_name=None)
def project_expense_update(request, expense_pk):
    expense = get_object_or_404(ProjectExpense, pk=expense_pk)
    project = expense.project

    if request.method == "POST":
        form = ProjectExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            messages.success(request, "Dépense modifiée avec succès.")
        else:
            messages.error(request, "Impossible de modifier la dépense.")
    return redirect("technique:technique_financial_project_detail", pk=project.pk)


@login_required
@user_passes_test(has_technique_access, login_url="/", redirect_field_name=None)
def project_expense_delete(request, expense_pk):
    expense = get_object_or_404(ProjectExpense, pk=expense_pk)
    project = expense.project

    if request.method == "POST":
        expense.delete()
        messages.success(request, "Dépense supprimée avec succès.")

    return redirect("technique:technique_financial_project_detail", pk=project.pk)

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
    project.refresh_amounts_from_expenses()
    expenses = project.expenses.all().order_by("due_date", "id")

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="budget_{project.reference}.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    x_margin = 2 * cm
    y = height - 2 * cm
    max_width = width - 2 * x_margin

    def wrap_text(text, font="Helvetica", size=10):
        lines_out = []
        if not text:
            return lines_out

        p.setFont(font, size)

        for raw_line in str(text).split("\n"):
            words = raw_line.split()
            current = ""
            for word in words:
                candidate = f"{current} {word}".strip()
                if pdfmetrics.stringWidth(candidate, font, size) <= max_width:
                    current = candidate
                else:
                    if current:
                        lines_out.append(current)
                    current = word
            if current:
                lines_out.append(current)

        return lines_out

    def write_line(text, font="Helvetica", size=10, leading=14):
        nonlocal y
        for line in wrap_text(text, font=font, size=size):
            if y < 2 * cm:
                p.showPage()
                y = height - 2 * cm
                p.setFont(font, size)
            p.setFont(font, size)
            p.drawString(x_margin, y, line)
            y -= leading

    p.setFont("Helvetica-Bold", 14)
    p.drawString(x_margin, y, f"Budget projet - {project.reference}")
    y -= 20

    write_line(f"Projet : {project.name}", size=11)
    write_line(f"Type : {project.get_type_display()}", size=11)
    write_line(f"Budget estimé : {project.total_estimated} €", size=11)
    write_line(f"Frais engagés : {project.frais_engages} €", size=11)
    write_line(f"Frais payés : {project.frais_payes} €", size=11)
    write_line(f"Restant à régler : {project.frais_restants} €", size=11)
    write_line(f"Reste à engager : {project.reste_a_engager} €", size=11)
    y -= 10

    p.setFont("Helvetica-Bold", 12)
    p.drawString(x_margin, y, "Dépenses du projet")
    y -= 18

    if expenses.exists():
        for expense in expenses:
            status = "Payée" if expense.is_paid else "À payer"
            line = (
                f"- {expense.label} | {expense.amount} € | {status} | "
                f"Échéance : {expense.due_date.strftime('%d/%m/%Y') if expense.due_date else '—'} | "
                f"Paiement : {expense.payment_date.strftime('%d/%m/%Y') if expense.payment_date else '—'}"
            )
            write_line(line, size=10)
            y -= 2
    else:
        write_line("Aucune dépense enregistrée.", size=10)

    p.showPage()
    p.save()
    return response

@login_required
@user_passes_test(has_technique_access, login_url="/", redirect_field_name=None)
def financial_project_csv(request, pk):
    project = get_object_or_404(TechnicalProject, pk=pk)
    project.refresh_amounts_from_expenses()
    expenses = project.expenses.all().order_by("due_date", "id")

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="budget_{project.reference}.csv"'

    writer = csv.writer(response, delimiter=";")
    writer.writerow(["Projet", project.name])
    writer.writerow(["Référence", project.reference])
    writer.writerow(["Type", project.get_type_display()])
    writer.writerow(["Budget estimé", project.total_estimated])
    writer.writerow(["Frais engagés", project.frais_engages])
    writer.writerow(["Frais payés", project.frais_payes])
    writer.writerow(["Restant à régler", project.frais_restants])
    writer.writerow(["Reste à engager", project.reste_a_engager])
    writer.writerow([])

    writer.writerow(["Libellé", "Montant", "Statut", "Échéance", "Date de paiement"])
    for expense in expenses:
        writer.writerow([
            expense.label,
            expense.amount,
            "Payée" if expense.is_paid else "À payer",
            expense.due_date.strftime("%d/%m/%Y") if expense.due_date else "",
            expense.payment_date.strftime("%d/%m/%Y") if expense.payment_date else "",
        ])

    return response


@login_required
@user_passes_test(has_technique_access, login_url="/", redirect_field_name=None)
def financial_project_excel(request, pk):
    project = get_object_or_404(TechnicalProject, pk=pk)
    project.refresh_amounts_from_expenses()
    expenses = project.expenses.all().order_by("due_date", "id")

    wb = Workbook()
    ws = wb.active
    ws.title = "Budget projet"

    ws.append(["Projet", project.name])
    ws.append(["Référence", project.reference])
    ws.append(["Type", project.get_type_display()])
    ws.append(["Budget estimé", float(project.total_estimated)])
    ws.append(["Frais engagés", float(project.frais_engages)])
    ws.append(["Frais payés", float(project.frais_payes)])
    ws.append(["Restant à régler", float(project.frais_restants)])
    ws.append(["Reste à engager", float(project.reste_a_engager)])
    ws.append([])

    ws.append(["Libellé", "Montant", "Statut", "Échéance", "Date de paiement"])
    for expense in expenses:
        ws.append([
            expense.label,
            float(expense.amount),
            "Payée" if expense.is_paid else "À payer",
            expense.due_date.strftime("%d/%m/%Y") if expense.due_date else "",
            expense.payment_date.strftime("%d/%m/%Y") if expense.payment_date else "",
        ])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="budget_{project.reference}.xlsx"'
    wb.save(response)
    return response

# ================== Suppression en masse ==================

@login_required
@user_passes_test(has_technique_access, login_url="/", redirect_field_name=None)
def bulk_delete_projects(request):
    """
    Vue pour supprimer plusieurs projets techniques en une seule action
    """
    if request.method != "POST":
        return redirect("technique:technique_financial_overview")

    ids = request.POST.getlist("project_ids")
    if not ids:
        messages.warning(request, "Aucun projet sélectionné.")
        return redirect("technique:technique_financial_overview")

    deleted_count, _ = TechnicalProject.objects.filter(id__in=ids).delete()
    messages.success(request, f"{deleted_count} projet(s) supprimé(s) avec succès.")
    return redirect("technique:technique_financial_overview")


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
            f"{deleted_count} document{'s' if deleted_count > 1 else ''} supprimé{'s' if deleted_count > 1 else ''} avec succès."
        )
    except Exception as e:
        messages.error(request, f"Erreur lors de la suppression : {str(e)}")
    
    return redirect("technique:documents_list")


