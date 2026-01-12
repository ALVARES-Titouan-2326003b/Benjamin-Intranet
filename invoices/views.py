from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django_filters.views import FilterView
from django.views.generic import DetailView, CreateView, UpdateView

from .filters import FactureFilter
from .forms import FactureForm, PieceJointeForm
from .models import Facture, PieceJointe


def is_finance(user):
    return user.is_staff or user.groups.filter(name='POLE_FINANCIER').exists()


# ================== Liste / Détail ==================

@method_decorator(login_required, name='dispatch')
class FactureListView(FilterView):
    model = Facture
    paginate_by = 20
    filterset_class = FactureFilter
    template_name = 'invoices/invoice_list.html'

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related('client')


@method_decorator(login_required, name='dispatch')
class FactureDetailView(DetailView):
    model = Facture
    template_name = 'invoices/invoice_detail.html'


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

@method_decorator([login_required, user_passes_test(is_finance)], name='dispatch')
class FactureCreateView(_PieceJointeMixin, CreateView):
    model = Facture
    form_class = FactureForm
    template_name = 'invoices/invoice_form.html'

    def get_success_url(self):
        messages.success(self.request, "Facture créée.")
        return reverse('invoices:detail', args=[self.object.pk])


@method_decorator([login_required, user_passes_test(is_finance)], name='dispatch')
class FactureUpdateView(_PieceJointeMixin, UpdateView):
    model = Facture
    form_class = FactureForm
    template_name = 'invoices/invoice_form.html'

    def get_success_url(self):
        messages.success(self.request, "Facture mise à jour.")
        return reverse('invoices:detail', args=[self.object.pk])


# ================== Relance Manuelle ==================

from django.views import View


@method_decorator([login_required, user_passes_test(is_finance)], name='dispatch')
class ManualInvoiceRemindersView(View):
    """
    Vue pour déclencher manuellement les relances de factures
    Lance la tâche check_and_send_invoice_reminders de tasks.py
    """

    def post(self, request, *args, **kwargs):
        # Importer la tâche Celery
        from .tasks import check_and_send_invoice_reminders

        # Exécuter la tâche de manière synchrone (pas via Celery)
        # Pour exécution immédiate sans passer par la queue
        result = check_and_send_invoice_reminders()

        # Préparer le message de feedback
        if result.get('success'):
            if result.get('relances_envoyees', 0) > 0:
                messages.success(
                    request,
                    f"Relance manuelle terminée ! "
                    f"{result['relances_envoyees']} email(s) envoyé(s) sur "
                    f"{result['factures_traitees']} facture(s) traitée(s)."
                )
            else:
                messages.info(
                    request,
                    f"Aucune relance à envoyer pour le moment. "
                    f"{result['factures_traitees']} facture(s) vérifiée(s)."
                )
        else:
            messages.error(
                request,
                f"Erreur lors de la relance : {result.get('message', 'Erreur inconnue')}"
            )

        # Rediriger vers la liste des factures
        return redirect('invoices:list')