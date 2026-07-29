from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models.deletion import ProtectedError
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from invoices.forms import SocieteForm
from invoices.models import Societe
from technique.models import DocumentTechnique
from user_access.user_test_functions import has_administratif_access


class AdministrativeSocieteForm(SocieteForm):
    """Le statut d'une société est géré par les actions retirer/réactiver."""

    class Meta(SocieteForm.Meta):
        fields = ["nom"]


def _companies_queryset():
    return (
        Societe.objects.annotate(
            invoice_count=Count("factures", distinct=True),
            project_count=Count("dossiers", distinct=True),
            activity_count=Count("activites", distinct=True),
            total_amount=Sum("factures__montant"),
            paid_amount=Sum(
                "factures__montant",
                filter=Q(factures__statut="paid"),
            ),
            overdue_count=Count(
                "factures",
                filter=Q(
                    factures__statut__in=["ongoing", "received"],
                    factures__echeance__lt=timezone.now(),
                ),
                distinct=True,
            ),
        )
        .order_by("nom")
    )


def _company_usage(company):
    usage = {
        "factures": company.factures.count(),
        "dossiers": company.dossiers.count(),
        "activites": company.activites.count(),
        "tampons": int(hasattr(company, "tampon")),
    }
    usage["total"] = sum(usage.values())
    return usage


@login_required
@user_passes_test(has_administratif_access, login_url="/", redirect_field_name=None)
def company_list_create(request):
    if request.method == "POST":
        form = AdministrativeSocieteForm(request.POST)
        if form.is_valid():
            company = form.save(commit=False)
            company.is_active = True
            company.save()
            messages.success(request, "Société ajoutée au référentiel.")
            return redirect("admin_societes")
    else:
        form = AdministrativeSocieteForm()

    companies = list(_companies_queryset())
    company_stats = {
        "active": sum(company.is_active for company in companies),
        "inactive": sum(not company.is_active for company in companies),
        "overdue": sum(company.overdue_count > 0 for company in companies),
    }
    return render(
        request,
        "invoices/societe_list.html",
        {
            "companies": companies,
            "company_stats": company_stats,
            "form": form,
        },
    )


@login_required
@user_passes_test(has_administratif_access, login_url="/", redirect_field_name=None)
def company_update(request, pk):
    company = get_object_or_404(Societe, pk=pk)
    if request.method == "POST":
        form = AdministrativeSocieteForm(request.POST, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, "Société mise à jour.")
            return redirect("admin_societes")
    else:
        form = AdministrativeSocieteForm(instance=company)

    companies = list(_companies_queryset())
    company_stats = {
        "active": sum(item.is_active for item in companies),
        "inactive": sum(not item.is_active for item in companies),
        "overdue": sum(item.overdue_count > 0 for item in companies),
    }
    return render(
        request,
        "invoices/societe_list.html",
        {
            "companies": companies,
            "company_stats": company_stats,
            "form": form,
            "editing_company": company,
        },
    )


@login_required
@user_passes_test(has_administratif_access, login_url="/", redirect_field_name=None)
def company_detail(request, pk):
    company = get_object_or_404(Societe, pk=pk)
    now = timezone.now()
    invoices = list(
        company.factures.select_related("fournisseur", "dossier")
        .prefetch_related("piecejointe_set")
        .order_by("-date_facture", "-date_soumission", "-id")
    )
    for invoice in invoices:
        invoice.is_overdue = bool(
            invoice.echeance
            and invoice.echeance < now
            and invoice.statut in {"ongoing", "received"}
        )

    dossiers = list(
        company.dossiers.annotate(
            document_count=Count("documents", distinct=True),
            related_invoice_count=Count("facture", distinct=True),
        ).order_by("-updated_at", "name")
    )
    documents = list(
        DocumentTechnique.objects.filter(project__societe=company)
        .select_related("project", "created_by")
        .order_by("-created_at")
    )
    invoice_stats = company.factures.aggregate(
        total_amount=Sum("montant"),
        paid_amount=Sum("montant", filter=Q(statut="paid")),
        overdue_count=Count(
            "pk",
            filter=Q(
                statut__in=["ongoing", "received"],
                echeance__lt=now,
            ),
        ),
    )
    return render(
        request,
        "invoices/societe_detail.html",
        {
            "company": company,
            "invoices": invoices,
            "dossiers": dossiers,
            "documents": documents,
            "activities_count": company.activites.count(),
            "total_amount": invoice_stats["total_amount"] or 0,
            "paid_amount": invoice_stats["paid_amount"] or 0,
            "overdue_count": invoice_stats["overdue_count"],
            "company_usage": _company_usage(company),
        },
    )


@require_POST
@login_required
@user_passes_test(has_administratif_access, login_url="/", redirect_field_name=None)
def company_delete(request, pk):
    company = get_object_or_404(Societe, pk=pk)
    usage = _company_usage(company)
    company_name = company.nom

    if usage["total"] == 0:
        try:
            company.delete()
            messages.success(request, f"La société « {company_name} » a été supprimée.")
        except ProtectedError:
            company.is_active = False
            company.save(update_fields=["is_active", "updated_at"])
            messages.warning(
                request,
                f"La société « {company_name} » possède encore des liaisons protégées : "
                "elle a été retirée des nouvelles sélections.",
            )
    elif company.is_active:
        company.is_active = False
        company.save(update_fields=["is_active", "updated_at"])
        messages.warning(
            request,
            f"La société « {company_name} » est déjà utilisée : elle a été retirée "
            "des nouvelles sélections afin de préserver l'historique.",
        )
    else:
        messages.info(
            request,
            f"La société « {company_name} » est déjà retirée des nouvelles sélections.",
        )
    return redirect("admin_societes")


@require_POST
@login_required
@user_passes_test(has_administratif_access, login_url="/", redirect_field_name=None)
def company_restore(request, pk):
    company = get_object_or_404(Societe, pk=pk)
    if not company.is_active:
        company.is_active = True
        company.save(update_fields=["is_active", "updated_at"])
        messages.success(
            request,
            f"La société « {company.nom} » est de nouveau disponible.",
        )
    return redirect("admin_societes")
