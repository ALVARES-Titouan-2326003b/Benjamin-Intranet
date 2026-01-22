from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

User = get_user_model()

class UserInvitationForm(forms.Form):
    """
    Correspond au formulaire pour inviter un utilisateur.

    Attributes:
        email (EmailField) : Email de l'utilisateur
        poles (ModelMultipleChoiceField) : Groupes de l'utilisateur
    """
    email = forms.EmailField(label="Email de l'utilisateur", required=True)
    poles = forms.ModelMultipleChoiceField(
        queryset=Group.objects.exclude(name='CEO'),
        widget=forms.CheckboxSelectMultiple,
        label="Pôles (Groupes)",
        required=True
    )

    def clean_email(self):
        """
        Vérifie que l'email est valide.
        """
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Un utilisateur avec cet email existe déjà.")
        return email

class AccountActivationForm(forms.Form):
    """
    Correspond au formulaire pour créer un compte.

    Attributes:
        first_name (str): Prénom de l'utilisateur
        last_name (str): Nom de famille de l'utilisateur
        username (str): Nom d'utilisateur
        password (str): Mot de passe
        password_confirm (str): Confirmation du mot de passe
    """
    first_name = forms.CharField(label="Prénom", max_length=150, required=True)
    last_name = forms.CharField(label="Nom", max_length=150, required=True)
    username = forms.CharField(label="Nom d'utilisateur souhaité", max_length=150, required=True)
    password = forms.CharField(label="Mot de passe", widget=forms.PasswordInput, required=True)
    password_confirm = forms.CharField(label="Confirmer le mot de passe", widget=forms.PasswordInput, required=True)

    def clean_username(self):
        """
        Vérifie que le nom d'utilisateur est valide.
        """
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Ce nom d'utilisateur est déjà pris.")
        return username

    def clean(self):
        """
        Vérifie que les mots de passe correspondent.
        """
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('password_confirm')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Les mots de passe ne correspondent pas.")
        return cleaned_data
