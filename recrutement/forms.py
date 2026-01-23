from django import forms
from .models import FicheDePoste, Candidat

class FicheDePosteForm(forms.ModelForm):
    """
    Correspond au formulaire pour la création d'une fiche de poste
    """
    class Meta:
        model = FicheDePoste
        fields = ["titre", "description", "competences_clees"]

class CVUploadForm(forms.ModelForm):
    """
    Correspond au formulaire pour l'enregistrement d'un CV
    """
    class Meta:
        model = Candidat
        fields = ["nom", "email", "cv_fichier"]
        widgets = {
            "cv_fichier": forms.ClearableFileInput(attrs={"accept": ".pdf,.txt,.docx"})
        }
 