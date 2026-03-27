from django import forms
from .models import DocumentTechnique, TechnicalProject, ProjectExpense


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
    class Meta:
        model = TechnicalProject
        fields = ["name", "reference", "type", "total_estimated"]


class TechnicalProjectFinanceForm(forms.ModelForm):
    """
    On ne modifie ici que le budget prévisionnel.
    Les montants engagés et payés sont calculés automatiquement
    depuis les dépenses projet.
    """

    class Meta:
        model = TechnicalProject
        fields = ["total_estimated"]


class DocumentTechniqueUpdateForm(forms.ModelForm):
    class Meta:
        model = DocumentTechnique
        fields = ["projet", "titre", "type_document"]


class ProjectExpenseForm(forms.ModelForm):
    class Meta:
        model = ProjectExpense
        fields = ["facture", "label", "amount", "is_paid", "due_date", "payment_date"]
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "payment_date": forms.DateInput(attrs={"type": "date"}),
        }
