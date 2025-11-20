from django import forms
from .models import DocumentTechnique, TechnicalProject


class DocumentTechniqueUploadForm(forms.ModelForm):
    class Meta:
        model = DocumentTechnique
        fields = ["projet", "titre", "type_document", "fichier"]
        widgets = {
            "fichier": forms.ClearableFileInput(
                attrs={"accept": ".pdf,.doc,.docx,.txt"}
            )
        }


class TechnicalProjectCreateForm(forms.ModelForm):
    """Créer un projet"""

    class Meta:
        model = TechnicalProject
        fields = ["name", "reference", "total_estimated"]


class TechnicalProjectFinanceForm(forms.ModelForm):
    """Modifier les données financières d'un projet"""

    class Meta:
        model = TechnicalProject
        fields = ["engaged_amount", "paid_amount", "total_estimated"]
