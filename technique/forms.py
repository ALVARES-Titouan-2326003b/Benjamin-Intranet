from django import forms
from .models import DocumentTechnique


class DocumentTechniqueUploadForm(forms.ModelForm):
    class Meta:
        model = DocumentTechnique
        fields = ["projet", "titre", "type_document", "fichier"]
        widgets = {
            "fichier": forms.ClearableFileInput(
                attrs={"accept": ".pdf,.doc,.docx,.txt"}
            )
        }
