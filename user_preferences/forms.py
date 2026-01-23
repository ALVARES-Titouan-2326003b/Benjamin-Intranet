from django import forms
from .models import UserPreference

class UserPreferenceForm(forms.ModelForm):
    """
    Correspond au formulaire des paramètres de l'utilisateur
    """
    class Meta:
        model = UserPreference
        fields = ['theme']
        widgets = {
            'theme': forms.RadioSelect(attrs={'class': 'theme-selector'}),
        }
        labels = {
            'theme': 'Thème de l\'interface',
        }
