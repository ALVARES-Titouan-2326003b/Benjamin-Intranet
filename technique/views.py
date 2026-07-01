import json
import csv
from decimal import Decimal
from django.views.decorators.http import require_http_methods
from reportlab.lib import colors
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from openpyxl import Workbook
from .services.documents import extract_text_from_file
from .services.ai_summary import summarize_document
from invoices.models import Facture
from .models import (
    DocumentTechnique,
    TechnicalProject,
    ProjectExpense,
    TechnicalEmail,
    TechnicalProjectHistory,
)
from .forms import (
    DocumentTechniqueUploadForm,
    TechnicalProjectCreateForm,
    TechnicalProjectFinanceForm,
    TechnicalProjectStatusForm,
    DocumentTechniqueUpdateForm,
    ProjectExpenseForm,
)
from user_access.user_test_functions import has_technique_access
from django.db.models import Q


def _get_available_project_invoices(project, current_expense=None):
    invoices = Facture.objects.filter(dossier=project).select_related(
        "fournisseur",
        "client",
        "collaborateur",
    )

    if current_expense and current_expense.facture_id:
        return invoices.filter(
            Q(project_expense__isnull=True) | Q(pk=current_expense.facture_id)
        ).order_by("-echeance", "id")

    return invoices.filter(project_expense__isnull=True).order_by("-echeance", "id")


def _history_value(value):
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _snapshot_project(project):
    return {
        "reference": project.reference,
        "name": project.name,
        "type": project.type,
        "status": project.status,
        "engaged_amount": _history_value(project.engaged_amount),
        "paid_amount": _history_value(project.paid_amount),
        "total_estimated": _history_value(project.total_estimated),
    }


def _snapshot_expense(expense):
    return {
        "id": expense.pk,
        "facture": expense.facture_id or "",
        "label": expense.label,
        "amount": _history_value(expense.amount),
        "is_paid": expense.is_paid,
        "due_date": _history_value(expense.due_date),
        "payment_date": _history_value(expense.payment_date),
    }


def _log_project_history(project, user, action, target_type, target_label="", before=None, after=None):
    TechnicalProjectHistory.objects.create(
        project=project if project and project.pk else None,
        project_reference=project.reference if project else "",
        project_name=project.name if project else "",
        user=user if getattr(user, "is_authenticated", False) else None,
        action=action,
        target_type=target_type,
        target_label=target_label,
        before=before or {},
        after=after or {},
    )


def _user_can_delete_technical_projects(user):
    if not getattr(user, "is_authenticated", False):
        return False
    return user.is_superuser or user.groups.filter(name="CEO").exists()


def _project_related_counts(project):
    project_labels = [project.reference, project.name]
    return {
        "documents": DocumentTechnique.objects.filter(projet__in=project_labels).count(),
        "factures": Facture.objects.filter(dossier=project).count(),
        "depenses": project.expenses.count(),
        "emails": project.emails.count(),
        "historique": project.history.count(),
    }


def _project_has_related_data(project):
    return any(_project_related_counts(project).values())


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

    paginator = Paginator(qs, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "technique/documents_list.html",
        {
            "documents": page_obj,
            "page_obj": page_obj,
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
    write_line(f"Dossier : {doc.projet or '—'}", size=11)
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
    Affiche la liste des dossiers techniques
    avec recherche et filtres.
    """
    projects = TechnicalProject.objects.all()

    q = (request.GET.get("q") or "").strip()
    reference = (request.GET.get("reference") or "").strip()
    project_type = (request.GET.get("type") or "").strip()
    project_status = (request.GET.get("status") or "").strip()
    sort = (request.GET.get("sort") or "").strip()

    if q:
        projects = projects.filter(
            Q(name__icontains=q) | Q(reference__icontains=q)
        )

    if reference:
        projects = projects.filter(reference__icontains=reference)

    if project_type:
        projects = projects.filter(type=project_type)

    if project_status:
        projects = projects.filter(status=project_status)

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
            project = form.save()
            _log_project_history(
                project=project,
                user=request.user,
                action="project_created",
                target_type="project",
                target_label=project.reference,
                after=_snapshot_project(project),
            )
            messages.success(request, "Dossier créé avec succès.")
            return redirect("technique:dossier_detail", pk=project.pk)
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
            "selected_status": project_status,
            "sort": sort,
            "type_choices": TechnicalProject.DOSSIER_TYPES,
            "status_choices": TechnicalProject.STATUS_CHOICES,
            "can_delete_projects": _user_can_delete_technical_projects(request.user),
        },
    )

@login_required
@user_passes_test(has_technique_access, login_url="/", redirect_field_name=None)
def financial_project_detail(request, pk):
    """
    Saisie des données financières + graphiques

    Args:
        request (HttpRequest): Requête HTTP
        pk (str): Identifiant du dossier
    """
    project = get_object_or_404(TechnicalProject, pk=pk)
    project.refresh_amounts_from_expenses()
    project_documents = DocumentTechnique.objects.filter(
        Q(projet=project.reference) | Q(projet=project.name)
    ).order_by("-created_at")[:10]

    if request.method == "POST" and "update_project_status" in request.POST:
        before_project = _snapshot_project(project)
        status_form = TechnicalProjectStatusForm(request.POST, instance=project)
        if status_form.is_valid():
            project = status_form.save()
            after_project = _snapshot_project(project)
            if before_project.get("status") != after_project.get("status"):
                _log_project_history(
                    project=project,
                    user=request.user,
                    action="status_updated",
                    target_type="project",
                    target_label=project.reference,
                    before={"status": before_project.get("status")},
                    after={"status": after_project.get("status")},
                )
            messages.success(request, "Statut du dossier mis à jour.")
            return redirect("technique:dossier_detail", pk=project.pk)
        form = TechnicalProjectFinanceForm(instance=project)
    elif request.method == "POST" and "total_estimated" in request.POST:
        before_project = _snapshot_project(project)
        form = TechnicalProjectFinanceForm(request.POST, instance=project)
        if form.is_valid():
            project = form.save()
            after_project = _snapshot_project(project)
            if before_project.get("total_estimated") != after_project.get("total_estimated"):
                _log_project_history(
                    project=project,
                    user=request.user,
                    action="budget_updated",
                    target_type="project",
                    target_label=project.reference,
                    before={"total_estimated": before_project.get("total_estimated")},
                    after={"total_estimated": after_project.get("total_estimated")},
                )
            messages.success(request, "Budget prévisionnel mis à jour.")
            return redirect("technique:dossier_detail", pk=project.pk)
    else:
        form = TechnicalProjectFinanceForm(instance=project)
        status_form = TechnicalProjectStatusForm(instance=project)

    if "status_form" not in locals():
        status_form = TechnicalProjectStatusForm(instance=project)

    expense_q = (request.GET.get("expense_q") or "").strip()
    expense_status = (request.GET.get("expense_status") or "").strip()

    expenses = project.expenses.select_related("facture").all().order_by("-due_date", "-id")
    invoices = (
        Facture.objects.filter(dossier=project)
        .select_related("fournisseur", "client", "collaborateur")
        .order_by("-echeance", "id")
    )
    history_entries = project.history.select_related("user").all()[:25]

    if expense_q:
        expenses = expenses.filter(label__icontains=expense_q)

    if expense_status == "paid":
        expenses = expenses.filter(is_paid=True)
    elif expense_status == "unpaid":
        expenses = expenses.filter(is_paid=False)

    invoice_supplier = (request.GET.get("invoice_supplier") or "").strip()
    invoice_status = (request.GET.get("invoice_status") or "").strip()
    invoice_due_from = (request.GET.get("invoice_due_from") or "").strip()
    invoice_due_to = (request.GET.get("invoice_due_to") or "").strip()
    invoice_association = (request.GET.get("invoice_association") or "").strip()

    if invoice_supplier:
        invoices = invoices.filter(fournisseur__nom__icontains=invoice_supplier)

    if invoice_status:
        invoices = invoices.filter(statut=invoice_status)

    if invoice_due_from:
        invoices = invoices.filter(echeance__date__gte=invoice_due_from)

    if invoice_due_to:
        invoices = invoices.filter(echeance__date__lte=invoice_due_to)

    if invoice_association == "linked":
        invoices = invoices.filter(project_expense__isnull=False)
    elif invoice_association == "unlinked":
        invoices = invoices.filter(project_expense__isnull=True)

    expense_form = ProjectExpenseForm()
    expense_form.fields["facture"].queryset = _get_available_project_invoices(project)

    for expense in expenses:
        expense.selectable_invoices = _get_available_project_invoices(project, current_expense=expense)

    for invoice in invoices:
        try:
            invoice.linked_expense = invoice.project_expense
        except Facture.project_expense.RelatedObjectDoesNotExist:
            invoice.linked_expense = None

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
            "status_form": status_form,
            "expense_form": expense_form,
            "expenses": expenses,
            "project_invoices": invoices,
            "history_entries": history_entries,
            "project_documents": project_documents,
            "expense_q": expense_q,
            "expense_status": expense_status,
            "invoice_supplier": invoice_supplier,
            "invoice_status": invoice_status,
            "invoice_due_from": invoice_due_from,
            "invoice_due_to": invoice_due_to,
            "invoice_association": invoice_association,
            "invoice_status_choices": Facture.STATUS,
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
        form.fields["facture"].queryset = _get_available_project_invoices(project)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.project = project
            expense.save()
            _log_project_history(
                project=project,
                user=request.user,
                action="expense_created",
                target_type="expense",
                target_label=expense.label,
                after=_snapshot_expense(expense),
            )
            messages.success(request, "Dépense ajoutée avec succès.")
        else:
            messages.error(request, "Impossible d'ajouter la dépense.")
    return redirect("technique:dossier_detail", pk=project.pk)



@login_required
@user_passes_test(has_technique_access, login_url="/", redirect_field_name=None)
def project_expense_update(request, expense_pk):
    expense = get_object_or_404(ProjectExpense, pk=expense_pk)
    project = expense.project

    if request.method == "POST":
        before_expense = _snapshot_expense(expense)
        form = ProjectExpenseForm(request.POST, instance=expense)
        form.fields["facture"].queryset = _get_available_project_invoices(project, current_expense=expense)
        if form.is_valid():
            expense = form.save()
            after_expense = _snapshot_expense(expense)
            if before_expense != after_expense:
                _log_project_history(
                    project=project,
                    user=request.user,
                    action="expense_updated",
                    target_type="expense",
                    target_label=expense.label,
                    before=before_expense,
                    after=after_expense,
                )
            messages.success(request, "Dépense modifiée avec succès.")
        else:
            messages.error(request, "Impossible de modifier la dépense.")
    return redirect("technique:dossier_detail", pk=project.pk)


@login_required
@user_passes_test(has_technique_access, login_url="/", redirect_field_name=None)
def project_expense_delete(request, expense_pk):
    expense = get_object_or_404(ProjectExpense, pk=expense_pk)
    project = expense.project

    if request.method == "POST":
        before_expense = _snapshot_expense(expense)
        expense.delete()
        _log_project_history(
            project=project,
            user=request.user,
            action="expense_deleted",
            target_type="expense",
            target_label=before_expense.get("label", ""),
            before=before_expense,
        )
        messages.success(request, "Dépense supprimée avec succès.")

    return redirect("technique:dossier_detail", pk=project.pk)

@login_required
@user_passes_test(has_technique_access, login_url="/", redirect_field_name=None)
def financial_project_pdf(request, pk):
    """
    Permet de télécharger le PDF de la vue financière

    Args:
        request (HttpRequest): Requête HTTP
        pk (str): Identifiant du dossier
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
    p.drawString(x_margin, y, f"Budget dossier - {project.reference}")
    y -= 20

    write_line(f"Dossier : {project.name}", size=11)
    write_line(f"Type : {project.get_type_display()}", size=11)
    write_line(f"Budget estimé : {project.total_estimated} €", size=11)
    write_line(f"Frais engagés : {project.frais_engages} €", size=11)
    write_line(f"Frais payés : {project.frais_payes} €", size=11)
    write_line(f"Restant à régler : {project.frais_restants} €", size=11)
    write_line(f"Reste à engager : {project.reste_a_engager} €", size=11)
    y -= 10

    p.setFont("Helvetica-Bold", 12)
    p.drawString(x_margin, y, "Dépenses du dossier")
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
    writer.writerow(["Dossier", project.name])
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
    ws.title = "Budget dossier"

    ws.append(["Dossier", project.name])
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


@login_required
@user_passes_test(has_technique_access, login_url="/", redirect_field_name=None)
def email_list(request):
    """
    Affiche uniquement les emails importés par l'utilisateur connecté.
    Chaque utilisateur a sa propre boîte — les mails sont strictement personnels.
    """
    # ── Filtre par utilisateur connecté ──────────────────────────────────────
    emails = TechnicalEmail.objects.select_related(
        "project", "imported_by"
    ).filter(
        imported_by=request.user  # ← chaque utilisateur ne voit QUE ses mails
    )

    q = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "").strip()
    project_id = (request.GET.get("project") or "").strip()
    has_attachments = (request.GET.get("has_attachments") or "").strip()

    if q:
        emails = emails.filter(
            Q(subject__icontains=q)
            | Q(sender__icontains=q)
            | Q(body__icontains=q)
            | Q(project__name__icontains=q)
            | Q(project__reference__icontains=q)
        )

    if status:
        emails = emails.filter(status=status)

    if project_id:
        emails = emails.filter(project_id=project_id)

    if has_attachments == "yes":
        emails = emails.filter(has_attachments=True)
    elif has_attachments == "no":
        emails = emails.filter(has_attachments=False)

    paginator = Paginator(emails, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "technique/email_list.html",
        {
            "emails": page_obj,
            "page_obj": page_obj,
            "q": q,
            "selected_status": status,
            "selected_project": project_id,
            "selected_has_attachments": has_attachments,
            "status_choices": TechnicalEmail.STATUS_CHOICES,
            "projects": TechnicalProject.objects.order_by("name"),
        },
    )



@login_required
@user_passes_test(has_technique_access, login_url="/", redirect_field_name=None)
def mail_assign_project(request, pk):
    email = get_object_or_404(TechnicalEmail, pk=pk, imported_by=request.user)

    if request.method == "POST":
        project_id = request.POST.get("project_id")
        if project_id:
            project = get_object_or_404(TechnicalProject, pk=project_id)
            email.project = project
            email.status = "classified"
            email.save(update_fields=["project", "status"])
            from technique.tasks import enqueue_email_attachment_processing
            processing = enqueue_email_attachment_processing(email)
            if processing.get("launched"):
                messages.success(
                    request,
                    "Email rattaché au dossier. Le traitement des pièces jointes a été lancé.",
                )
            else:
                messages.warning(
                    request,
                    "Email rattaché au dossier, mais le traitement des pièces jointes "
                    f"n'a pas pu être lancé : {processing.get('error', 'aucune pièce jointe')}",
                )

    return redirect("technique:mail_detail", pk=email.pk)


@login_required
@user_passes_test(has_technique_access, login_url="/", redirect_field_name=None)
@require_http_methods(["POST"])
def email_import_gmail(request):
    """
    Déclenche l'import des emails Gmail vers TechnicalEmail.

    URL  : POST /technique/email/import/
    Auth : utilisateur du groupe POLE_TECHNIQUE

    Returns:
        JsonResponse : {
            'success': bool,
            'imported': int,
            'skipped':  int,
            'errors':   int,
            'message':  str   # résumé lisible
        }
    """
    from technique.services.gmail_import import import_technique_emails

    try:
        stats = import_technique_emails(user=request.user, max_results=50)

        message = (
            f"{stats['imported']} email(s) importé(s), "
            f"{stats['skipped']} déjà présent(s), "
            f"{stats['errors']} erreur(s), "
            f"{stats['attachments_imported']} pièce(s) jointe(s) enregistrée(s)."
        )

        return JsonResponse({
            "success": True,
            "imported": stats["imported"],
            "skipped": stats["skipped"],
            "errors": stats["errors"],
            "attachments_imported": stats["attachments_imported"],
            "attachment_errors": stats["attachment_errors"],
            "attachment_processing_launched": stats["attachment_processing_launched"],
            "message": message,
        })

    except ValueError as exc:
        # Pas de token OAuth
        return JsonResponse({"success": False, "message": str(exc)}, status=400)

    except Exception as exc:
        import traceback
        traceback.print_exc()
        return JsonResponse(
            {"success": False, "message": f"Erreur serveur : {str(exc)}"},
            status=500,
        )


@login_required
@user_passes_test(has_technique_access, login_url="/", redirect_field_name=None)
def email_detail(request, pk):
    """
    Affiche le détail d'un email technique avec :
    - headers (expéditeur, destinataires, cc, date)
    - corps du message
    - pièces jointes téléchargeables
    - formulaire de rattachement à un dossier
    - documents techniques liés (via les pièces jointes)
    """
    email = get_object_or_404(
        TechnicalEmail.objects.select_related("project", "imported_by")
        .prefetch_related("attachments__linked_document"),
        pk=pk,
        imported_by=request.user,
    )

    return render(
        request,
        "technique/email_detail.html",
        {
            "email": email,
            # Liste des dossiers pour le sélecteur de rattachement
            "projects": TechnicalProject.objects.order_by("reference"),
        },
    )


@login_required
@user_passes_test(has_technique_access, login_url="/", redirect_field_name=None)
@require_http_methods(["POST"])
def email_ai_classify(request, pk):
    """
    Lance la classification IA pour un email specifique.

    URL    : POST /technique/email/<pk>/classify/
    Return : JsonResponse {
        success, project_id, project_label, confidence, reason, saved, status
    }
    """
    from technique.services.ai_classify import classify_and_save

    email = get_object_or_404(TechnicalEmail, pk=pk, imported_by=request.user)
    projects = TechnicalProject.objects.order_by("reference")

    # sleep=0 : pas de pause pour un email individuel (l'utilisateur attend la reponse)
    result = classify_and_save(email, projects, sleep=0)
    processing = {"launched": False, "attachments": 0, "task_id": ""}
    email.refresh_from_db(fields=["status", "project"])
    if result.get("saved") and email.status == "classified" and email.project_id:
        from technique.tasks import enqueue_email_attachment_processing
        processing = enqueue_email_attachment_processing(email)

    project_label = None
    if result.get("project_id"):
        try:
            p = TechnicalProject.objects.get(pk=result["project_id"])
            project_label = f"{p.reference} – {p.name}"
        except TechnicalProject.DoesNotExist:
            pass

    return JsonResponse({
        "success": result["success"],
        "project_id": result.get("project_id"),
        "project_label": project_label,
        "confidence": result.get("confidence"),
        "reason": result.get("reason"),
        "saved": result.get("saved", False),
        "status": email.status,
        "error": result.get("error"),
        "attachment_processing": processing,
    })


# ── Vue 2 : Classement IA en masse ───────────────────────────────────────────

@login_required
@user_passes_test(has_technique_access, login_url="/", redirect_field_name=None)
@require_http_methods(["POST"])
def email_ai_classify_bulk(request):
    """
    Lance la classification IA sur tous les emails au statut 'unassigned'.
    Une pause de BULK_SLEEP secondes est inseree entre chaque appel Groq
    pour eviter le rate limit 429.

    URL    : POST /technique/email/classify-bulk/
    Return : JsonResponse {
        success, classified, pending, skipped, errors, total, message
    }
    """
    from technique.services.ai_classify import classify_and_save, BULK_SLEEP

    emails = TechnicalEmail.objects.filter(
        status="unassigned",
        imported_by=request.user,
    ).order_by("-received_at")
    projects = list(TechnicalProject.objects.order_by("reference"))

    stats = {
        "classified": 0,
        "pending": 0,
        "skipped": 0,
        "errors": 0,
        "attachment_processing_launched": 0,
    }
    total = emails.count()

    print(f"[bulk_classify] Debut classement de {total} email(s) non classes (pause={BULK_SLEEP}s entre chaque)")

    for i, email in enumerate(emails, 1):
        try:
            # La pause BULK_SLEEP est inseree APRES chaque appel Groq, sauf le dernier
            sleep = BULK_SLEEP if i < total else 0
            result = classify_and_save(email, projects, sleep=sleep)

            if not result["success"]:
                stats["errors"] += 1
            elif result["saved"]:
                # email.status a ete mis a jour en base par classify_and_save, on le relit
                email.refresh_from_db(fields=["status"])
                if email.status == "classified":
                    stats["classified"] += 1
                    from technique.tasks import enqueue_email_attachment_processing
                    processing = enqueue_email_attachment_processing(email)
                    if processing.get("launched"):
                        stats["attachment_processing_launched"] += processing.get(
                            "attachments",
                            0,
                        )
                else:
                    stats["pending"] += 1
            else:
                stats["skipped"] += 1

        except Exception as exc:
            print(f"[bulk_classify] Erreur email {email.pk} : {exc}")
            stats["errors"] += 1

    processed = stats["classified"] + stats["pending"] + stats["skipped"] + stats["errors"]

    print(
        f"[bulk_classify] Termine : "
        f"{stats['classified']} classes, {stats['pending']} a valider, "
        f"{stats['skipped']} non attribues, {stats['errors']} erreurs"
    )

    return JsonResponse({
        "success": True,
        "classified": stats["classified"],
        "pending": stats["pending"],
        "skipped": stats["skipped"],
        "errors": stats["errors"],
        "total": processed,
        "attachment_processing_launched": stats["attachment_processing_launched"],
        "message": (
            f"{stats['classified']} classé(s) automatiquement, "
            f"{stats['pending']} à valider, "
            f"{stats['skipped']} non attribué(s), "
            f"{stats['errors']} erreur(s) "
            f"— sur {processed} email(s) traité(s)."
        ),
    })
# ================== Suppression en masse ==================

@login_required
@user_passes_test(has_technique_access, login_url="/", redirect_field_name=None)
def bulk_delete_projects(request):
    """
    Vue pour supprimer plusieurs dossiers techniques en une seule action
    """
    if request.method != "POST":
        return redirect("technique:dossiers_list")

    if not _user_can_delete_technical_projects(request.user):
        messages.error(request, "Suppression refusée : validation CEO / superadmin obligatoire.")
        return redirect("technique:dossiers_list")

    ids = request.POST.getlist("project_ids")
    if not ids:
        messages.warning(request, "Aucun dossier sélectionné.")
        return redirect("technique:dossiers_list")

    projects_to_delete = list(TechnicalProject.objects.filter(id__in=ids))
    projects_with_related_data = [
        project for project in projects_to_delete if _project_has_related_data(project)
    ]
    if projects_with_related_data and request.POST.get("confirm_related") != "1":
        messages.error(
            request,
            "Suppression interrompue : au moins un dossier contient des éléments liés. "
            "Confirmation explicite CEO / superadmin requise.",
        )
        return redirect("technique:dossiers_list")

    for project in projects_to_delete:
        _log_project_history(
            project=project,
            user=request.user,
            action="project_deleted",
            target_type="project",
            target_label=project.reference,
            before=_snapshot_project(project),
        )

    TechnicalProject.objects.filter(id__in=[p.id for p in projects_to_delete]).delete()
    deleted_count = len(projects_to_delete)
    messages.success(request, f"{deleted_count} dossier(s) supprimé(s) avec succès.")
    return redirect("technique:dossiers_list")


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
