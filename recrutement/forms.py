from django import forms
from .models import FicheDePoste, Candidat

class FicheDePosteForm(forms.ModelForm):
    class Meta:
        model = FicheDePoste
        fields = ["titre", "description", "competences_clees"]

class CVUploadForm(forms.ModelForm):
    class Meta:
        model = Candidat
        fields = ["nom", "email", "cv_fichier"]
        widgets = {
            "cv_fichier": forms.ClearableFileInput(attrs={"accept": ".pdf,.txt,.docx"})
        }
 