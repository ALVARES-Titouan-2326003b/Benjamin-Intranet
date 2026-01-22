from django.views.generic.edit import UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import get_object_or_404
from .models import UserPreference
from .forms import UserPreferenceForm

class SettingsView(LoginRequiredMixin, UpdateView):
    model = UserPreference
    form_class = UserPreferenceForm
    template_name = 'user_preferences/preferences.html'
    success_url = reverse_lazy('settings')

    def get_object(self):
        # Ensure we return the preferences of the current user
        return get_object_or_404(UserPreference, user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Vos préférences ont été enregistrées avec succès.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Paramètres utilisateur"
        return context
