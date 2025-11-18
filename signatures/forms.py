from django import forms
from .models import Document, SignatureUser, Tampon


class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ["titre", "fichier"]


class SignatureUserForm(forms.ModelForm):
    class Meta:
        model = SignatureUser
        fields = ["image"]


class TamponForm(forms.ModelForm):
    class Meta:
        model = Tampon
        fields = ["nom", "image"]


class PlacementForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ["stamp_x", "stamp_y", "sig_x", "sig_y"]
        widgets = {
            "stamp_x": forms.NumberInput(attrs={"step": 1, "min": 0, "max": 100}),
            "stamp_y": forms.NumberInput(attrs={"step": 1, "min": 0, "max": 100}),
            "sig_x": forms.NumberInput(attrs={"step": 1, "min": 0, "max": 100}),
            "sig_y": forms.NumberInput(attrs={"step": 1, "min": 0, "max": 100}),
        }
