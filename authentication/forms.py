from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

User = get_user_model()

class UserInvitationForm(forms.Form):
    email = forms.EmailField(label="Email de l'utilisateur", required=True)
    poles = forms.ModelMultipleChoiceField(
        queryset=Group.objects.exclude(name='CEO'),
        widget=forms.CheckboxSelectMultiple,
        label="Pôles (Groupes)",
        required=True
    )

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Un utilisateur avec cet email existe déjà.")
        return email

class AccountActivationForm(forms.Form):
    first_name = forms.CharField(label="Prénom", max_length=150, required=True)
    last_name = forms.CharField(label="Nom", max_length=150, required=True)
    username = forms.CharField(label="Nom d'utilisateur souhaité", max_length=150, required=True)
    password = forms.CharField(label="Mot de passe", widget=forms.PasswordInput, required=True)
    password_confirm = forms.CharField(label="Confirmer le mot de passe", widget=forms.PasswordInput, required=True)

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Ce nom d'utilisateur est déjà pris.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('password_confirm')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Les mots de passe ne correspondent pas.")
        return cleaned_data
