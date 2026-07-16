import io

from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.utils.decorators import method_decorator
from django_filters.views import FilterView
from django.views.generic import DetailView, CreateView, UpdateView, TemplateView

from openpyxl import Workbook
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

from user_access.user_test_functions import (
    has_finance_access,
    has_ceo_access,
    has_all_poles_access,
    can_read_facture,
    can_create_facture,
    can_edit_facture,
    can_change_facture_status,
    has_collaborateur_access,
)
from .filters import FactureFilter
from .forms import FactureForm, PieceJointeForm, SocieteForm
from .models import (
    Facture,
    PieceJointe,
    FactureHistorique,
    InvoiceReminderSettings,
    Societe,
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
        - Finance/CEO : Voir toutes les factures
        - Collaborateur : Voir uniquement ses factures assignées
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
            .order_by('-date_soumission', '-id')
        )
        user = self.request.user
        
        # Tous les pôles ont une vue d'ensemble des factures.
        if has_all_poles_access(user):
            return qs
            
        # Sinon -> Voir seulement ses factures
        return qs.filter(Q(collaborateur=user) | Q(created_by=user) | Q(demandeur=user))

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
            'Service',
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
        doc = SimpleDocTemplate(output, pagesize=letter)

        data = [[
            'ID',
            'N° facture',
            'Société',
            'Affaire',
            'Dossier',
            'Service',
            'Montant',
            'Statut',
            'Échéance',
        ]]

        for invoice in queryset:
            data.append([
                invoice.id,
                invoice.numero_facture or '',
                str(invoice.societe) if invoice.societe else '',
                invoice.affaire or '',
                str(invoice.dossier) if invoice.dossier else '',
                invoice.get_service_display() if invoice.service else '',
                f"{invoice.montant:.2f}" if invoice.montant is not None else '',
                invoice.get_statut_display(),
                invoice.echeance.strftime('%Y-%m-%d') if invoice.echeance else '',
            ])

        table = Table(data, repeatRows=1, hAlign='LEFT')
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ])
        table.setStyle(table_style)

        doc.build([table])

        output.seek(0)
        response = HttpResponse(output.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="factures.pdf"'
        return response

    def get_context_data( self, *, object_list = ..., **kwargs):
        context = super().get_context_data(**kwargs)
        can_manage_finance = has_finance_access(self.request.user) or has_ceo_access(self.request.user)
        context['access_finance'] = can_manage_finance
        context['can_create_invoice'] = can_create_facture(self.request.user)
        context['can_export_invoices'] = can_manage_finance
        context['can_manage_bulk_delete'] = can_manage_finance
        context['can_manage_manual_reminders'] = can_manage_finance
        context['can_view_dashboard'] = can_manage_finance
        context['can_view_exports'] = can_manage_finance
        context['can_view_anomalies'] = can_manage_finance
        if can_manage_finance:
            from django.contrib.auth import get_user_model

            user_model = get_user_model()
            context["gmail_senders"] = (
                user_model.objects.filter(
                    is_active=True,
                    oauth_token__provider="google",
                )
                .distinct()
                .order_by("last_name", "first_name", "username")
            )
            context["reminder_settings"] = (
                InvoiceReminderSettings.objects.select_related("sender")
                .filter(pk=1)
                .first()
            )
        return context

@method_decorator([login_required, user_passes_test(can_read_facture, login_url="/", redirect_field_name=None)], name="dispatch")
class FactureDetailView(DetailView):
    """
    Vue pour afficher les détails d'une facture

    Permissions:
        - Finance/CEO : Voir toutes les factures
        - Collaborateur : Voir uniquement ses factures assignées
    """
    model = Facture
    template_name = 'invoices/invoice_detail.html'

    def get_queryset(self):
        qs = super().get_queryset().select_related('collaborateur', 'demandeur', 'dossier', 'societe')
        user = self.request.user
        
        # Tous les pôles ont une vue d'ensemble des factures.
        if has_all_poles_access(user):
            return qs
            
        # Sinon -> Voir seulement ses factures
        return qs.filter(Q(collaborateur=user) | Q(created_by=user) | Q(demandeur=user))

    def get_context_data(self, *, object_list=..., **kwargs):
        context = super().get_context_data(**kwargs)
        context['access_finance'] = has_finance_access(self.request.user) or has_ceo_access(self.request.user)
        context['can_edit_invoice'] = can_edit_facture(self.request.user, self.object)
        return context


# ================== Pièce jointe ==================

class _PieceJointeMixin:
    def get_piece_form(self):
        if self.request.method == "POST":
            return PieceJointeForm(self.request.POST, self.request.FILES)
        return PieceJointeForm()

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
        form.instance.service = get_invoice_service_for_user(self.request.user)
        
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user_ceo"] = has_ceo_access(self.request.user)
        context["is_collaborateur"] = has_collaborateur_access(self.request.user)
        context["can_change_invoice_status"] = can_change_facture_status(self.request.user)
        return context


@method_decorator([login_required, user_passes_test(can_create_facture, login_url="/", redirect_field_name=None)], name='dispatch')
class FactureUpdateView(_PieceJointeMixin, UpdateView):
    """
    Vue pour mettre à jour une facture
    """
    model = Facture
    template_name = 'invoices/invoice_form.html'

    def get_queryset(self):
        # Hors finance/CEO, les utilisateurs ne peuvent éditer que leurs propres factures.
        queryset = super().get_queryset()
        if not can_change_facture_status(self.request.user):
            return queryset.filter(
                Q(collaborateur=self.request.user)
                | Q(created_by=self.request.user)
                | Q(demandeur=self.request.user)
            )
        return queryset

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

# ================== Relance Manuelle ==================

@method_decorator([login_required, user_passes_test(can_change_facture_status, login_url="/", redirect_field_name=None)], name='dispatch')
class ManualInvoiceRemindersView(View):
    """
    Vue pour déclencher manuellement les relances de factures.
    Récupère le délai de relance depuis le formulaire et le passe
    à la fonction tasks.check_and_send_invoice_reminders()
    """

    def post(self, request, *args, **kwargs):
        # Récupérer le délai de relance depuis le formulaire
        try:
            delai_relance = int(request.POST.get('delai_relance', 1))

            # Validation : minimum 1 jour
            if delai_relance < 1:
                messages.error(request, "Le délai de relance doit être au minimum de 1 jour.")
                return redirect('invoices:list')

        except (ValueError, TypeError):
            messages.error(request, "Délai de relance invalide.")
            return redirect('invoices:list')

        # Importer la tâche et l'exécuter avec le délai
        from .tasks import check_and_send_invoice_reminders

        result = check_and_send_invoice_reminders(delai_relance=delai_relance)

        # Préparer le message de feedback
        if result.get('success'):
            if result.get('relances_envoyees', 0) > 0:
                messages.success(
                    request,
                    f"Relance manuelle terminée avec délai de {delai_relance} jour{['','s'][delai_relance>1]} ! "
                    f"{result['relances_envoyees']} email{['','s'][result['relances_envoyees']>1]} envoyé{['','s'][result['relances_envoyees']>1]} sur "
                    f"{result['factures_traitees']} facture{['','s'][result['factures_traitees']>1]} traitée{['','s'][result['factures_traitees']>1]}."
                )
            else:
                messages.info(
                    request,
                    f"Aucune relance à envoyer pour le moment (délai : {delai_relance} jour{['','s'][delai_relance>1]}). "
                    f"{result['factures_traitees']} facture{['','s'][result['factures_traitees']>1]} vérifiée{['','s'][result['factures_traitees']>1]}."
                )
        else:
            messages.error(
                request,
                f"Erreur lors de la relance : {result.get('message', 'Erreur inconnue')}"
            )

        return redirect('invoices:list')

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


@method_decorator([login_required, user_passes_test(can_change_facture_status, login_url="/", redirect_field_name=None)], name="dispatch")
class InvoiceReminderSettingsView(View):
    def post(self, request, *args, **kwargs):
        sender_id = request.POST.get("sender_id")
        from django.contrib.auth import get_user_model

        sender = (
            get_user_model()
            .objects.filter(pk=sender_id, is_active=True, oauth_token__provider="google")
            .first()
        )
        if not sender:
            messages.error(request, "Sélectionnez un utilisateur actif ayant synchronisé Gmail.")
            return redirect("invoices:list")

        settings_obj, _ = InvoiceReminderSettings.objects.get_or_create(pk=1)
        settings_obj.sender = sender
        settings_obj.save(update_fields=["sender", "updated_at"])
        messages.success(request, f"{sender.email} est désormais l'expéditeur des relances.")
        return redirect("invoices:list")


@method_decorator([login_required, user_passes_test(can_change_facture_status, login_url="/", redirect_field_name=None)], name='dispatch')
class InvoiceAnomaliesView(TemplateView):
    template_name = 'invoices/anomalies.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['anomalies'] = get_invoice_anomalies()
        return context


@login_required
@user_passes_test(can_change_facture_status, login_url="/", redirect_field_name=None)
def societe_list_create(request):
    if request.method == "POST":
        form = SocieteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Société pré-enregistrée.")
            return redirect("invoices:societes")
    else:
        form = SocieteForm()

    companies = Societe.objects.annotate(
        invoice_count=Count("factures", distinct=True),
        total_amount=Sum("factures__montant"),
        paid_amount=Sum("factures__montant", filter=Q(factures__statut="paid")),
        overdue_count=Count(
            "factures",
            filter=Q(
                factures__statut__in=["ongoing", "received"],
                factures__echeance__lt=timezone.now(),
            ),
            distinct=True,
        ),
    ).order_by("nom")
    return render(
        request,
        "invoices/societe_list.html",
        {"companies": companies, "form": form},
    )


@login_required
@user_passes_test(can_change_facture_status, login_url="/", redirect_field_name=None)
def societe_update(request, pk):
    company = get_object_or_404(Societe, pk=pk)
    if request.method == "POST":
        form = SocieteForm(request.POST, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, "Société mise à jour.")
            return redirect("invoices:societes")
    else:
        form = SocieteForm(instance=company)
    companies = Societe.objects.annotate(
        invoice_count=Count("factures", distinct=True),
        total_amount=Sum("factures__montant"),
        paid_amount=Sum("factures__montant", filter=Q(factures__statut="paid")),
        overdue_count=Count(
            "factures",
            filter=Q(
                factures__statut__in=["ongoing", "received"],
                factures__echeance__lt=timezone.now(),
            ),
            distinct=True,
        ),
    ).order_by("nom")
    return render(
        request,
        "invoices/societe_list.html",
        {"companies": companies, "form": form, "editing_company": company},
    )
