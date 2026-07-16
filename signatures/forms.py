from django import forms
from django.db.models import Q
from invoices.models import Societe
from .models import Document, SignatureUser, Tampon


class DocumentUploadForm(forms.ModelForm):
    """
    Formulaire pour enregistrer un document
    """
    class Meta:
        model = Document
        fields = ["titre", "fichier"]


class SignatureUserForm(forms.ModelForm):
    """
    Formulaire pour enregistrer la signature d'un utilisateur
    """
    class Meta:
        model = SignatureUser
        fields = ["image"]


class TamponForm(forms.ModelForm):
    """
    Formulaire pour créer/modifier le tampon
    """
    class Meta:
        model = Tampon
        fields = ["societe", "image", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = Societe.objects.filter(is_active=True)
        if self.instance.societe_id:
            queryset = Societe.objects.filter(Q(is_active=True) | Q(pk=self.instance.societe_id))
        self.fields["societe"].queryset = queryset.order_by("nom")


class PlacementForm(forms.ModelForm):
    """
    Formulaire pour enregistrer la position de base de la signature
    """
    class Meta:
        model = Document
        fields = ["stamp_x", "stamp_y", "sig_x", "sig_y"]
        widgets = {
            "stamp_x": forms.NumberInput(attrs={"step": 1, "min": 0, "max": 100}),
            "stamp_y": forms.NumberInput(attrs={"step": 1, "min": 0, "max": 100}),
            "sig_x": forms.NumberInput(attrs={"step": 1, "min": 0, "max": 100}),
            "sig_y": forms.NumberInput(attrs={"step": 1, "min": 0, "max": 100}),
        }
