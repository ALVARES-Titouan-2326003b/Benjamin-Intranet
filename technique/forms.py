from django import forms
from .models import DocumentTechnique, TechnicalProject, ProjectExpense


class DocumentTechniqueUploadForm(forms.ModelForm):
    class Meta:
        model = DocumentTechnique
        fields = ["project", "titre", "fichier"]
        widgets = {
            "project": forms.Select(attrs={"class": "form-control"}),
            "titre": forms.TextInput(attrs={"class": "form-control"}),
            "fichier": forms.ClearableFileInput(
                attrs={"accept": ".pdf,.doc,.docx,.txt", "class": "form-control"}
            )
        }


class TechnicalProjectCreateForm(forms.ModelForm):
    class Meta:
        model = TechnicalProject
        fields = ["reference", "name", "status", "type"]
        widgets = {
            "reference": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex. TECH-001"}),
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nom du dossier"}),
            "status": forms.Select(attrs={"class": "form-control"}),
            "type": forms.Select(attrs={"class": "form-control"}),
        }


class TechnicalProjectFinanceForm(forms.ModelForm):
    """
    On ne modifie ici que le budget prévisionnel.
    Les montants engagés et payés sont calculés automatiquement
    depuis les dépenses du dossier.
    """

    class Meta:
        model = TechnicalProject
        fields = ["total_estimated"]
        widgets = {
            "total_estimated": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        }


class TechnicalProjectStatusForm(forms.ModelForm):
    class Meta:
        model = TechnicalProject
        fields = ["status"]
        widgets = {
            "status": forms.Select(attrs={"class": "form-control"}),
        }


class DocumentTechniqueUpdateForm(forms.ModelForm):
    class Meta:
        model = DocumentTechnique
        fields = ["project", "titre"]
        widgets = {
            "project": forms.Select(attrs={"class": "form-control"}),
            "titre": forms.TextInput(attrs={"class": "form-control"}),
        }


class ProjectExpenseForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["facture"].required = False
        self.fields["facture"].empty_label = "-- Aucune facture associée --"
        self.fields["facture"].help_text = (
            "Optionnel : une dépense peut être saisie sans facture issue du pôle financier."
        )

    class Meta:
        model = ProjectExpense
        fields = ["facture", "label", "amount", "is_paid", "due_date", "payment_date"]
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "payment_date": forms.DateInput(attrs={"type": "date"}),
        }
