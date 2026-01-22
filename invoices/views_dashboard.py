from typing import Any, Dict

from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.db.models import Sum, Count, Q
from django.utils import timezone

from user_access.user_test_functions import has_finance_access
from .models import Facture
from django.db.models.functions import TruncMonth

@method_decorator([login_required, user_passes_test(has_finance_access, login_url="/", redirect_field_name=None)], name='dispatch')
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
        @user_passes_test(has_finance_access)
    """
    template_name = "invoices/dashboard.html"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        
        # 1. Base QuerySet
        qs = Facture.objects.all()
        now = timezone.now()

        # 2. KPIs
        # Total facturé (Toutes factures confondues)
        total_aggregate = qs.aggregate(
            total=Sum('montant'),
            count=Count('id')
        )
        total_amount = total_aggregate['total'] or 0
        total_count = total_aggregate['count'] or 0

        # Montant Payé
        paid_aggregate = qs.filter(statut='Payee').aggregate(total=Sum('montant'))
        paid_amount = paid_aggregate['total'] or 0

        # En attente (Tout ce qui n'est pas payé ni annulé/archivé)
        pending_qs = qs.exclude(statut__in=['Payee', 'Archivee'])
        pending_aggregate = pending_qs.aggregate(total=Sum('montant'))
        pending_amount = pending_aggregate['total'] or 0

        # En Retard (Non payée et date dépassée) OU Statut explicitement 'En retard'
        overdue_qs = qs.filter(
            Q(statut__in=['Recue', 'En cours', 'En retard']),
            echeance__lt=now
        )
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
        }

        # 3. Chart 1: Répartition par Statut (Pie Chart)
        # Returns list of dicts: [{'statut': 'Payée', 'total': 1200}, ...]
        status_data = qs.values('statut').annotate(count=Count('id'), total=Sum('montant')).order_by('statut')
        
        # Prepare for Chart.js
        chart_status_labels = [item['statut'] or 'Indéfini' for item in status_data]
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
            overdue_qs.values('fournisseur')
            .annotate(
                total_retard=Sum('montant'),
                count_retard=Count('id')
            )
            .order_by('-total_retard')[:5]
        )
        
        context['risky_suppliers'] = risky_suppliers

        return context
