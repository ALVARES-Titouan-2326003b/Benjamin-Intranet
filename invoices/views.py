import io
from html import escape

from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.utils.decorators import method_decorator
from django_filters.views import FilterView
from django.views.generic import DetailView, CreateView, UpdateView, TemplateView

from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

from user_access.user_test_functions import (
    has_finance_access,
    has_ceo_access,
    can_read_facture,
    can_create_facture,
    can_edit_facture,
    can_change_facture_status,
    has_collaborateur_access,
)
from .filters import FactureFilter
from .forms import FactureForm, PieceJointeForm
from .models import (
    Facture,
    PieceJointe,
    FactureHistorique,
)
from .services.email import send_invoice_submission_email
from .services.quality import get_invoice_anomalies


USER_GROUP_TO_INVOICE_SERVICE = {
    "POLE_DEVELOPPEMENT": "developpement",
    "POLE_ADMINISTRATIF": "administratif",
    "POLE_TECHNIQUE": "technique",
    "POLE_PROMOTION": "promotion",
    "POLE_INVESTISSEMENT": "investissement",
    "POLE_FINANCIER": "financier",
}


def visible_invoices_for(user, queryset=None):
    """Applique la portée de consultation des factures de manière centralisée."""
    queryset = queryset if queryset is not None else Facture.objects.all()
    if has_finance_access(user):
        return queryset
    return queryset.filter(created_by=user)


def get_invoice_service_for_user(user):
    group_names = set(user.groups.values_list("name", flat=True))
    for group_name, service in USER_GROUP_TO_INVOICE_SERVICE.items():
        if group_name in group_names:
            return service
    return ""


# ================== Liste / Détail ==================

@method_decorator([login_required, user_passes_test(can_read_facture, login_url="/", redirect_field_name=None)], name="dispatch")
class FactureListView(FilterView):
    """
    Vue affichant la liste des factures avec filtres.

    Permissions:
        - Superadmin/Finance : voir toutes les factures
        - Autres utilisateurs : voir uniquement les factures qu'ils ont créées
    """
    model = Facture
    paginate_by = 20
    filterset_class = FactureFilter
    template_name = 'invoices/invoice_list.html'

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related('collaborateur', 'demandeur', 'dossier', 'societe')
            .order_by(
                '-date_soumission',
                '-id',
            )
        )
        user = self.request.user
        
        return visible_invoices_for(user, qs)

    def get(self, request, *args, **kwargs):
        # Vérifier si c'est une demande d'export
        export = request.GET.get('export')

        if export in ('xlsx', 'pdf'):
            # Applique les filtres et récupère le queryset filtré
            queryset = self.get_queryset()
            filterset = self.get_filterset_class()(request.GET, queryset=queryset)
            filtered_qs = filterset.qs

            if export == 'xlsx':
                return self.export_to_excel(filtered_qs)
            elif export == 'pdf':
                return self.export_to_pdf(filtered_qs)

        # Comportement normal : appel du parent
        return super().get(request, *args, **kwargs)

    def export_to_excel(self, queryset):
        wb = Workbook()
        ws = wb.active
        ws.title = 'Factures'

        headers = [
            'ID',
            'N° facture',
            'Société',
            'Affaire',
            'Dossier',
            'Pôle',
            'Fournisseur',
            'Montant TTC',
            'Statut',
            'Date facture',
            'Échéance',
            'Priorité',
            'Demandeur',
        ]
        ws.append(headers)

        for invoice in queryset:
            ws.append([
                invoice.id,
                invoice.numero_facture or '',
                str(invoice.societe) if invoice.societe else '',
                invoice.affaire or '',
                str(invoice.dossier) if invoice.dossier else '',
                invoice.get_service_display() if invoice.service else '',
                str(invoice.fournisseur) if invoice.fournisseur else '',
                invoice.montant or '',
                invoice.get_statut_display(),
                invoice.date_facture.strftime('%Y-%m-%d') if invoice.date_facture else '',
                invoice.echeance.strftime('%Y-%m-%d') if invoice.echeance else '',
                invoice.get_priorite_display() if invoice.priorite else '',
                invoice.demandeur.username if invoice.demandeur else '',
            ])

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="factures.xlsx"'
        return response

    def export_to_pdf(self, queryset):
        output = io.BytesIO()
        doc = SimpleDocTemplate(
            output,
            pagesize=landscape(A4),
            leftMargin=24,
            rightMargin=24,
            topMargin=24,
            bottomMargin=24,
            title="Export des factures",
        )

        header_style = ParagraphStyle(
            "InvoiceExportHeader",
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=8,
            textColor=colors.white,
            alignment=TA_LEFT,
        )
        cell_style = ParagraphStyle(
            "InvoiceExportCell",
            fontName="Helvetica",
            fontSize=6.7,
            leading=8,
            textColor=colors.black,
            alignment=TA_LEFT,
            splitLongWords=True,
        )

        def cell(value, style=cell_style):
            return Paragraph(escape(str(value or "—")), style)

        headers = [
            "ID",
            "N° facture",
            "Société",
            "Dossier / affaire",
            "Pôle",
            "Fournisseur",
            "Montant",
            "Statut",
            "Échéance",
        ]
        data = [[cell(label, header_style) for label in headers]]

        for invoice in queryset:
            case_label = str(invoice.dossier) if invoice.dossier else invoice.affaire
            data.append([
                cell(invoice.id),
                cell(invoice.numero_facture),
                cell(invoice.societe),
                cell(case_label),
                cell(invoice.get_service_display() if invoice.service else "—"),
                cell(invoice.fournisseur),
                cell(f"{invoice.montant:.2f} €" if invoice.montant is not None else "—"),
                cell(invoice.get_statut_display()),
                cell(invoice.echeance.strftime("%d/%m/%Y") if invoice.echeance else "—"),
            ])

        table = Table(
            data,
            colWidths=[85, 72, 88, 155, 72, 105, 62, 70, 72],
            repeatRows=1,
            hAlign="LEFT",
        )
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.whitesmoke]),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ])
        table.setStyle(table_style)

        doc.build([table])

        output.seek(0)
        response = HttpResponse(output.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="factures.pdf"'
        return response

    def get_context_data( self, *, object_list = ..., **kwargs):
        context = super().get_context_data(**kwargs)
        query_params = self.request.GET.copy()
        query_params.pop("page", None)
        query_params.pop("export", None)
        context["invoice_query_params"] = query_params.urlencode()

        can_manage_finance = has_finance_access(self.request.user) or has_ceo_access(self.request.user)
        context['access_finance'] = can_manage_finance
        context['can_create_invoice'] = can_create_facture(self.request.user)
        context['can_export_invoices'] = can_manage_finance
        context['can_manage_bulk_delete'] = can_manage_finance
        context['can_view_dashboard'] = can_manage_finance
        context['can_view_exports'] = can_manage_finance
        context['can_view_anomalies'] = can_manage_finance
        return context

@method_decorator([login_required, user_passes_test(can_read_facture, login_url="/", redirect_field_name=None)], name="dispatch")
class FactureDetailView(DetailView):
    """
    Vue pour afficher les détails d'une facture

    Permissions:
        - Superadmin/Finance : voir toutes les factures
        - Autres utilisateurs : voir uniquement les factures qu'ils ont créées
    """
    model = Facture
    template_name = 'invoices/invoice_detail.html'

    def get_queryset(self):
        qs = super().get_queryset().select_related('collaborateur', 'demandeur', 'dossier', 'societe')
        user = self.request.user
        
        return visible_invoices_for(user, qs)

    def get_context_data(self, *, object_list=..., **kwargs):
        context = super().get_context_data(**kwargs)
        context['access_finance'] = has_finance_access(self.request.user) or has_ceo_access(self.request.user)
        context['can_edit_invoice'] = can_edit_facture(self.request.user, self.object)
        return context


# ================== Pièce jointe ==================

class _PieceJointeMixin:
    def is_invoice_attachment_required(self):
        """Une facture doit toujours avoir un fichier lors de sa création."""
        return self.object is None

    def get_piece_form(self):
        kwargs = {"required": self.is_invoice_attachment_required()}
        if self.request.method == "POST":
            return PieceJointeForm(self.request.POST, self.request.FILES, **kwargs)
        return PieceJointeForm(**kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.setdefault("piece_form", self.get_piece_form())
        return ctx

    def form_valid(self, form):
        # Sauvegarde de la facture
        response = super().form_valid(form)
        # Puis éventuelle pièce jointe
        piece_form = self.get_piece_form()
        if piece_form.is_valid():
            f = piece_form.cleaned_data.get("fichier")
            if f:
                PieceJointe.objects.create(facture=self.object, fichier=f)
        else:
            return self.form_invalid(form)
        return response

    def post(self, request, *args, **kwargs):
        if hasattr(self, "get_object"):
            try:
                self.object = self.get_object()
            except Exception:
                self.object = None
        else:
            self.object = None

        form = self.get_form()
        piece_form = self.get_piece_form()
        if form.is_valid() and piece_form.is_valid():
            return self.form_valid(form)
        return self.render_to_response(self.get_context_data(form=form, piece_form=piece_form))


# ================== Create / Update ==================

@method_decorator([login_required, user_passes_test(can_create_facture, login_url="/", redirect_field_name=None)], name='dispatch')
class FactureCreateView(_PieceJointeMixin, CreateView):
    """
    Vue pour créer une facture
    """
    model = Facture
    template_name = 'invoices/invoice_form.html'

    def get_form_class(self):
        # Seul le pôle finance garde le champ statut à la création.
        if not can_change_facture_status(self.request.user):
            from .forms import FactureFormCollaborateur
            return FactureFormCollaborateur
        return FactureForm

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.demandeur = self.request.user
        form.instance.collaborateur = self.request.user

        response = super().form_valid(form)
        FactureHistorique.objects.create(
            facture=self.object,
            action='user_action',
            new_status=self.object.statut,
            user=self.request.user,
            details=f"Facture créée par {self.request.user.username}"
        )
        send_invoice_submission_email(self.object)
        return response

    def get_success_url(self):
        messages.success(self.request, "Facture créée.")
        return reverse('invoices:detail', args=[self.object.pk])

    def get_initial(self):
        initial = super().get_initial()
        initial.setdefault("service", get_invoice_service_for_user(self.request.user))
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user_ceo"] = has_ceo_access(self.request.user)
        context["is_collaborateur"] = has_collaborateur_access(self.request.user)
        context["can_change_invoice_status"] = can_change_facture_status(self.request.user)
        context["invoice_attachment_required"] = True
        return context


@method_decorator([login_required, user_passes_test(can_create_facture, login_url="/", redirect_field_name=None)], name='dispatch')
class FactureUpdateView(_PieceJointeMixin, UpdateView):
    """
    Vue pour mettre à jour une facture
    """
    model = Facture
    template_name = 'invoices/invoice_form.html'

    def get_queryset(self):
        # Hors superadmin/finance, seule la personne ayant créé la facture peut l'éditer.
        queryset = super().get_queryset()
        return visible_invoices_for(self.request.user, queryset)

    def get_form_class(self):
        # Seul le pôle finance garde le champ statut en édition.
        if not can_change_facture_status(self.request.user):
            from .forms import FactureFormCollaborateur
            return FactureFormCollaborateur
        return FactureForm

    def form_valid(self, form):
        old_status = self.get_object().statut
        response = super().form_valid(form)
        new_status = self.object.statut

        FactureHistorique.objects.create(
            facture=self.object,
            action='user_action',
            old_status=old_status,
            new_status=new_status,
            user=self.request.user,
            details=f"Facture modifiée par {self.request.user.username}"
        )

        return response

    def get_success_url(self):
        messages.success(self.request, "Facture mise à jour.")
        return reverse('invoices:detail', args=[self.object.pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user_ceo"] = has_ceo_access(self.request.user)
        context["is_collaborateur"] = has_collaborateur_access(self.request.user)
        context["can_change_invoice_status"] = can_change_facture_status(self.request.user)
        return context

# ================== Suppression en masse ==================

@method_decorator([login_required, user_passes_test(can_change_facture_status, login_url="/", redirect_field_name=None)], name='dispatch')
class BulkDeleteInvoicesView(View):
    """
    Vue pour supprimer plusieurs factures en une seule action
    """

    def post(self, request, *args, **kwargs):
        # Récupérer les IDs des factures sélectionnées
        invoice_ids = request.POST.getlist('invoice_ids')
        
        if not invoice_ids:
            messages.warning(request, "Aucune facture sélectionnée.")
            return redirect('invoices:list')
        
        try:
            # Supprimer les factures
            deleted_count = Facture.objects.filter(id__in=invoice_ids).delete()[0]
            
            messages.success(
                request,
                f"{deleted_count} facture{['','s'][deleted_count>1]} supprimée{['','s'][deleted_count>1]} avec succès."
            )
        except Exception as e:
            messages.error(request, f"Erreur lors de la suppression : {str(e)}")
        
        return redirect('invoices:list')


@method_decorator([login_required, user_passes_test(can_change_facture_status, login_url="/", redirect_field_name=None)], name='dispatch')
class InvoiceAnomaliesView(TemplateView):
    template_name = 'invoices/anomalies.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['anomalies'] = get_invoice_anomalies()
        return context
