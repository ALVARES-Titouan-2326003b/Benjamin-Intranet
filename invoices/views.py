from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.urls import reverse
from django.utils.decorators import method_decorator
from django_filters.views import FilterView
from django.views.generic import DetailView, CreateView, UpdateView

from user_access.user_test_functions import has_finance_access, is_ceo, can_read_facture
from .filters import FactureFilter
from .forms import FactureForm, PieceJointeForm
from .models import Facture, PieceJointe


# ================== Liste / Détail ==================

@method_decorator([login_required, user_passes_test(can_read_facture, login_url="/", redirect_field_name=None)], name="dispatch")
class FactureListView(FilterView):
    model = Facture
    paginate_by = 20
    filterset_class = FactureFilter
    template_name = 'invoices/invoice_list.html'

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related('client')

    def get_extra_context(self):
        return {"access_finance": has_finance_access(self.request.user)}


@method_decorator([login_required, user_passes_test(can_read_facture, login_url="/", redirect_field_name=None)], name="dispatch")
class FactureDetailView(DetailView):
    model = Facture
    template_name = 'invoices/invoice_detail.html'

    def get_extra_context(self):
        return {"access_finance": has_finance_access(self.request.user)}


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

@method_decorator([login_required, user_passes_test(has_finance_access, login_url="/", redirect_field_name=None)], name='dispatch')
class FactureCreateView(_PieceJointeMixin, CreateView):
    model = Facture
    form_class = FactureForm
    template_name = 'invoices/invoice_form.html'

    def get_success_url(self):
        messages.success(self.request, "Facture créée.")
        return reverse('invoices:detail', args=[self.object.pk])

    def get_context_data(self, **kwargs):
        return {"user_ceo": is_ceo(self.request.user)}


@method_decorator([login_required, user_passes_test(has_finance_access, login_url="/", redirect_field_name=None)], name='dispatch')
class FactureUpdateView(_PieceJointeMixin, UpdateView):
    model = Facture
    form_class = FactureForm
    template_name = 'invoices/invoice_form.html'

    def get_success_url(self):
        messages.success(self.request, "Facture mise à jour.")
        return reverse('invoices:detail', args=[self.object.pk])

    def get_context_data(self, **kwargs):
        return {"user_ceo": is_ceo(self.request.user)}