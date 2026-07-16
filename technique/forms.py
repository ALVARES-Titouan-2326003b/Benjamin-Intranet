from django import forms
from django.contrib.auth import get_user_model
from .models import (
    DocumentTechnique,
    ProjectExpense,
    TechnicalProject,
    TechnicalProjectAction,
    TechnicalProjectKeyDate,
)

User = get_user_model()


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


class TechnicalProjectActionForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].required = False
        self.fields["assigned_to"].empty_label = "-- Non assignée --"
        self.fields["assigned_to"].queryset = (
            User.objects.filter(is_active=True, groups__name="POLE_TECHNIQUE")
            .distinct()
            .order_by("username")
        )

    class Meta:
        model = TechnicalProjectAction
        fields = ["title", "assigned_to", "status", "priority", "description", "due_date"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Action à réaliser"}),
            "assigned_to": forms.Select(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
            "priority": forms.Select(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "due_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }


class TechnicalProjectKeyDateForm(forms.ModelForm):
    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].required = False
        self.fields["document"].required = False
        self.fields["document"].empty_label = "-- Aucun document --"
        self.fields["action"].required = False
        self.fields["action"].empty_label = "-- Aucune action --"

        if project is not None:
            self.fields["document"].queryset = project.documents.order_by("-created_at")
            self.fields["action"].queryset = project.actions.order_by("due_date", "id")

    class Meta:
        model = TechnicalProjectKeyDate
        fields = ["label", "date", "status", "comment", "document", "action"]
        widgets = {
            "label": forms.TextInput(attrs={"class": "form-control", "placeholder": "Libellé de la date clé"}),
            "date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
            "comment": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "document": forms.Select(attrs={"class": "form-control"}),
            "action": forms.Select(attrs={"class": "form-control"}),
        }
