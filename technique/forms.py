from django import forms
from django.contrib.auth import get_user_model
from django.db import models
from invoices.models import Societe
from config.upload_validation import validate_uploaded_file
from .models import (
    DocumentTechnique,
    ProjectExpense,
    TechnicalProject,
    TechnicalProjectAction,
    TechnicalProjectKeyDate,
)
from .widgets import CompanyProjectSelect

User = get_user_model()


class DocumentTechniqueUploadForm(forms.ModelForm):
    societe = forms.ModelChoiceField(
        queryset=Societe.objects.none(),
        required=False,
        label="Société",
        empty_label="-- Sélectionner une société --",
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["societe"].queryset = Societe.objects.filter(is_active=True).order_by("nom")
        self.fields["project"].queryset = TechnicalProject.objects.filter(
            archived_at__isnull=True
        ).order_by("reference")
        self.fields["project"].required = False
        initial_project_id = self.initial.get("project")
        if initial_project_id and not self.initial.get("societe"):
            initial_project = self.fields["project"].queryset.filter(pk=initial_project_id).first()
            if initial_project:
                self.fields["societe"].initial = initial_project.societe_id

    def clean(self):
        cleaned_data = super().clean()
        societe = cleaned_data.get("societe")
        project = cleaned_data.get("project")
        if project and not societe:
            self.add_error("societe", "Sélectionnez une société avant de choisir un dossier.")
        elif project and project.societe_id != societe.pk:
            self.add_error("project", "Ce dossier n’est pas rattaché à la société sélectionnée.")
        return cleaned_data

    def clean_fichier(self):
        fichier = self.cleaned_data["fichier"]
        validate_uploaded_file(fichier, {".pdf", ".doc", ".docx", ".txt"})
        return fichier

    class Meta:
        model = DocumentTechnique
        fields = ["societe", "project", "titre", "fichier"]
        widgets = {
            "project": CompanyProjectSelect(attrs={"class": "form-control"}),
            "titre": forms.TextInput(attrs={"class": "form-control"}),
            "fichier": forms.ClearableFileInput(
                attrs={"accept": ".pdf,.doc,.docx,.txt", "class": "form-control"}
            )
        }


class TechnicalProjectCreateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["societe"].queryset = Societe.objects.filter(is_active=True).order_by("nom")
        self.fields["societe"].required = True
        self.fields["societe"].empty_label = "-- Sélectionner une société --"

    class Meta:
        model = TechnicalProject
        fields = ["reference", "name", "societe", "status", "type"]
        widgets = {
            "reference": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex. TECH-001"}),
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nom du dossier"}),
            "societe": forms.Select(attrs={"class": "form-control"}),
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
    societe = forms.ModelChoiceField(
        queryset=Societe.objects.none(),
        required=False,
        label="Société",
        empty_label="-- Sélectionner une société --",
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        companies = Societe.objects.filter(is_active=True)
        if self.instance.project_id:
            companies = Societe.objects.filter(
                models.Q(is_active=True) | models.Q(pk=self.instance.project.societe_id)
            )
            self.fields["societe"].initial = self.instance.project.societe_id
        self.fields["societe"].queryset = companies.order_by("nom")
        projects = TechnicalProject.objects.filter(archived_at__isnull=True)
        if self.instance.project_id:
            projects = TechnicalProject.objects.filter(
                models.Q(archived_at__isnull=True) | models.Q(pk=self.instance.project_id)
            )
        self.fields["project"].queryset = projects.order_by("reference")
        self.fields["project"].required = False

    def clean(self):
        cleaned_data = super().clean()
        societe = cleaned_data.get("societe")
        project = cleaned_data.get("project")
        if project and not societe:
            self.add_error("societe", "Sélectionnez une société avant de choisir un dossier.")
        elif project and project.societe_id != societe.pk:
            self.add_error("project", "Ce dossier n’est pas rattaché à la société sélectionnée.")
        return cleaned_data

    class Meta:
        model = DocumentTechnique
        fields = ["societe", "project", "titre"]
        widgets = {
            "project": CompanyProjectSelect(attrs={"class": "form-control"}),
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
        self.fields["documents"].required = False
        self.fields["action"].required = False
        self.fields["action"].empty_label = "-- Aucune action --"

        if project is not None:
            self.fields["documents"].queryset = project.documents.order_by("-created_at")
            self.fields["action"].queryset = project.actions.order_by("due_date", "id")

    class Meta:
        model = TechnicalProjectKeyDate
        fields = ["label", "date", "status", "comment", "documents", "action"]
        widgets = {
            "label": forms.TextInput(attrs={"class": "form-control", "placeholder": "Libellé de la date clé"}),
            "date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
            "comment": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "documents": forms.CheckboxSelectMultiple(attrs={"class": "key-date-document-checkbox"}),
            "action": forms.Select(attrs={"class": "form-control"}),
        }
