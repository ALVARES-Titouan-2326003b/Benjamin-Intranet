from urllib.parse import urlencode
from typing import Any, Dict

from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.db.models import Sum, Count, Q
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date

from user_access.user_test_functions import can_change_facture_status
from .models import Facture
from django.db.models.functions import TruncMonth
from .services.quality import get_invoice_anomalies


OPEN_STATUSES = ["ongoing", "received"]
INACTIVE_STATUSES = ["paid", "archived"]


def _invoice_list_url(**params):
    clean_params = {key: value for key, value in params.items() if value not in (None, "")}
    query = urlencode(clean_params)
    url = reverse("invoices:list")
    return f"{url}?{query}" if query else url


def _total(value):
    return value or 0

@method_decorator([login_required, user_passes_test(can_change_facture_status, login_url="/", redirect_field_name=None)], name='dispatch')
class DashboardView(TemplateView):
    """
    Tableau de bord financier avec KPIs et graphiques.

    Context data:

        kpi: {
            total_amount, total_count, paid_amount,
            pending_amount, overdue_amount,
            overdue_count, paid_percent
        }

        chart_status: { labels, data }  Pie chart statuts
        chart_monthly: { labels, data }  Bar chart évolution mensuelle
        risky_suppliers: QuerySet  Top 5 fournisseurs en retard

    Permissions:
        @user_passes_test(can_change_facture_status)
    """
    template_name = "invoices/dashboard.html"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        
        # 1. Base QuerySet filtré par le tableau de bord
        base_qs = Facture.objects.select_related("dossier", "fournisseur")
        qs = self._filtered_queryset(base_qs)
        now = timezone.now()
        overdue_filter = Q(statut__in=OPEN_STATUSES, echeance__lt=now)
        pending_filter = ~Q(statut__in=INACTIVE_STATUSES)

        # 2. KPIs
        # Total facturé (Toutes factures confondues)
        total_aggregate = qs.aggregate(
            total=Sum('montant'),
            count=Count('id')
        )
        total_amount = total_aggregate['total'] or 0
        total_count = total_aggregate['count'] or 0

        # Montant Payé
        paid_aggregate = qs.filter(statut='paid').aggregate(total=Sum('montant'))
        paid_amount = paid_aggregate['total'] or 0

        # En attente (Tout ce qui n'est pas payé ni annulé/archivé)
        pending_qs = qs.filter(pending_filter)
        pending_aggregate = pending_qs.aggregate(total=Sum('montant'))
        pending_amount = pending_aggregate['total'] or 0

        # En Retard (Non payée et date dépassée) OU Statut explicitement 'En retard'
        overdue_qs = qs.filter(overdue_filter)
        overdue_aggregate = overdue_qs.aggregate(
            total=Sum('montant'),
            count=Count('id')
        )
        overdue_amount = overdue_aggregate['total'] or 0
        overdue_count = overdue_aggregate['count'] or 0

        context['kpi'] = {
            'total_amount': total_amount,
            'total_count': total_count,
            'paid_amount': paid_amount,
            'pending_amount': pending_amount,
            'overdue_amount': overdue_amount,
            'overdue_count': overdue_count,
            'paid_percent': (paid_amount / total_amount * 100) if total_amount > 0 else 0,
            'pending_percent': (pending_amount / total_amount * 100) if total_amount > 0 else 0,
            'avg_processing_days': self._average_processing_days(qs),
        }
        context["active_filters"] = self._active_filters()
        context["status_choices"] = Facture.STATUS
        context["priority_choices"] = Facture.PRIORITY_CHOICES
        context["reset_dashboard_url"] = reverse("invoices:dashboard")

        # 3. Chart 1: Répartition par Statut (Pie Chart)
        # Returns list of dicts: [{'statut': 'Payée', 'total': 1200}, ...]
        status_data = qs.values('statut').annotate(count=Count('id'), total=Sum('montant')).order_by('statut')
        
        # Prepare for Chart.js
        status_labels = dict(Facture.STATUS)
        chart_status_labels = [status_labels.get(item['statut'], item['statut'] or 'Indéfini') for item in status_data]
        chart_status_data = [item['count'] for item in status_data]
        # Colors could be assigned here or in JS. Let's send raw data.
        context['chart_status'] = {
            'labels': chart_status_labels,
            'data': chart_status_data,
        }

        # 4. Chart 2: Evolution Mensuelle (Bar/Line)
        # Group by Month of echeance
        # Postgres specific: TruncMonth
        monthly_data = (
            qs.annotate(month=TruncMonth('echeance'))
            .values('month')
            .annotate(total=Sum('montant'))
            .order_by('month')
        )

        chart_month_labels = []
        chart_month_values = []
        
        for item in monthly_data:
            m = item['month']
            if m:
                # Format: "Jan 2024"
                label = m.strftime('%b %Y')
            else:
                label = "Sans date"
            
            chart_month_labels.append(label)
            chart_month_values.append(item['total'] or 0)

        context['chart_monthly'] = {
            'labels': chart_month_labels,
            'data': chart_month_values,
        }

        # 5. Risk Analysis: Top Suppliers with Overdue Invoices
        # Group by fournisseur, filter overdue
        risky_suppliers = (
            overdue_qs.values('fournisseur', 'fournisseur__nom')
            .annotate(
                total_retard=Sum('montant'),
                count_retard=Count('id')
            )
            .order_by('-total_retard')[:5]
        )
        
        context['risky_suppliers'] = risky_suppliers
        context['top_suppliers'] = (
            qs.values('fournisseur', 'fournisseur__nom')
            .annotate(total=Sum('montant'), count=Count('id'))
            .order_by('-total')[:5]
        )
        anomalies = get_invoice_anomalies(qs)
        context['anomaly_count'] = len(anomalies)
        context["company_rows"] = self._company_rows(qs, pending_filter, overdue_filter)
        context["project_rows"] = self._project_rows(qs, pending_filter, overdue_filter)
        context["business_alerts"] = self._business_alerts(qs, overdue_filter)

        return context

    def _active_filters(self):
        fields = ["echeance_min", "echeance_max", "societe", "dossier", "statut", "priorite"]
        return {field: (self.request.GET.get(field) or "").strip() for field in fields}

    def _filtered_queryset(self, queryset):
        filters = self._active_filters()
        if filters["societe"]:
            queryset = queryset.filter(societe__icontains=filters["societe"])
        if filters["dossier"]:
            dossier_search = filters["dossier"]
            queryset = queryset.filter(
                Q(affaire__icontains=dossier_search)
                | Q(dossier__reference__icontains=dossier_search)
                | Q(dossier__name__icontains=dossier_search)
                | Q(dossier__affaire__icontains=dossier_search)
            )
        if filters["statut"]:
            queryset = queryset.filter(statut=filters["statut"])
        if filters["priorite"]:
            queryset = queryset.filter(priorite=filters["priorite"])

        start = parse_date(filters["echeance_min"]) if filters["echeance_min"] else None
        end = parse_date(filters["echeance_max"]) if filters["echeance_max"] else None
        if start:
            queryset = queryset.filter(echeance__date__gte=start)
        if end:
            queryset = queryset.filter(echeance__date__lte=end)
        return queryset

    def _company_rows(self, queryset, pending_filter, overdue_filter):
        rows = (
            queryset.exclude(societe="")
            .values("societe")
            .annotate(
                total=Sum("montant"),
                count=Count("id"),
                pending_total=Sum("montant", filter=pending_filter),
                overdue_total=Sum("montant", filter=overdue_filter),
                overdue_count=Count("id", filter=overdue_filter),
            )
            .order_by("-total", "societe")[:5]
        )
        return [
            {
                **row,
                "total": _total(row["total"]),
                "pending_total": _total(row["pending_total"]),
                "overdue_total": _total(row["overdue_total"]),
                "invoice_url": _invoice_list_url(societe=row["societe"]),
                "overdue_url": _invoice_list_url(societe=row["societe"], echeance_max=timezone.localdate().isoformat()),
            }
            for row in rows
        ]

    def _project_rows(self, queryset, pending_filter, overdue_filter):
        rows = (
            queryset.exclude(dossier__isnull=True)
            .values("dossier", "dossier__reference", "dossier__name", "dossier__affaire")
            .annotate(
                total=Sum("montant"),
                count=Count("id"),
                open_count=Count("id", filter=pending_filter),
                overdue_total=Sum("montant", filter=overdue_filter),
                overdue_count=Count("id", filter=overdue_filter),
                urgent_count=Count("id", filter=Q(priorite__in=["urgent", "critical"])),
            )
            .order_by("-open_count", "-overdue_total", "-total")[:5]
        )
        return [
            {
                **row,
                "label": self._project_label(row),
                "total": _total(row["total"]),
                "overdue_total": _total(row["overdue_total"]),
                "invoice_url": _invoice_list_url(dossier=row["dossier__reference"] or row["dossier__name"]),
                "project_url": reverse("technique:dossier_detail", args=[row["dossier"]]),
            }
            for row in rows
        ]

    def _business_alerts(self, queryset, overdue_filter):
        missing_company_count = queryset.filter(Q(societe="") | Q(societe__isnull=True)).count()
        missing_project_count = queryset.filter(dossier__isnull=True).count()
        inconsistent_project_count = sum(
            1
            for invoice in queryset.exclude(dossier__isnull=True)
            if invoice.affaire and invoice.affaire != str(invoice.dossier)
        )
        overdue_project_count = (
            queryset.filter(overdue_filter)
            .exclude(dossier__isnull=True)
            .values("dossier")
            .distinct()
            .count()
        )
        return [
            {
                "label": "Factures sans société",
                "count": missing_company_count,
                "severity": "warning",
                "url": _invoice_list_url(societe=""),
            },
            {
                "label": "Factures sans dossier",
                "count": missing_project_count,
                "severity": "warning",
                "url": _invoice_list_url(dossier=""),
            },
            {
                "label": "Affaire différente du dossier lié",
                "count": inconsistent_project_count,
                "severity": "warning",
                "url": _invoice_list_url(),
            },
            {
                "label": "Dossiers avec factures en retard",
                "count": overdue_project_count,
                "severity": "danger",
                "url": _invoice_list_url(echeance_max=timezone.localdate().isoformat()),
            },
        ]

    def _project_label(self, row):
        reference = row["dossier__reference"] or ""
        name = row["dossier__affaire"] or row["dossier__name"] or ""
        if reference and name:
            return f"{reference} - {name}"
        return reference or name or "Dossier sans libellé"

    def _average_processing_days(self, queryset):
        durations = []
        paid_invoices = queryset.filter(statut='paid').prefetch_related('historique')
        for invoice in paid_invoices:
            history = list(invoice.historique.all().order_by('created_at'))
            paid_event = next((event for event in history if event.new_status == 'paid'), None)
            if not paid_event or not history:
                continue
            durations.append((paid_event.created_at - history[0].created_at).total_seconds() / 86400)
        if not durations:
            return None
        return sum(durations) / len(durations)
