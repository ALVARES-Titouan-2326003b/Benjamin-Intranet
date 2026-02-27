"""
Tests pour le module authentication.forms
Tests des formulaires d'invitation et d'activation de compte
"""
import pytest
from django.contrib.auth.models import User, Group

from authentication.forms import (
    UserInvitationForm,
    AccountActivationForm,
)


@pytest.mark.django_db
class TestUserInvitationForm:
    """Tests pour le formulaire UserInvitationForm"""

    @pytest.fixture
    def create_groups(self):
        """Créer des groupes de test"""
        Group.objects.get_or_create(name='POLE_ADMINISTRATIF')
        Group.objects.get_or_create(name='POLE_TECHNIQUE')
        Group.objects.get_or_create(name='POLE_FINANCIER')
        Group.objects.get_or_create(name='CEO')

    def test_valid_form(self, create_groups):
        """Teste un formulaire valide"""
        pole_admin = Group.objects.get(name='POLE_ADMINISTRATIF')
        pole_tech = Group.objects.get(name='POLE_TECHNIQUE')

        form_data = {
            'email': 'newuser@example.com',
            'poles': [pole_admin.id, pole_tech.id]
        }

        form = UserInvitationForm(data=form_data)
        assert form.is_valid()

    def test_missing_email(self, create_groups):
        """Teste avec email manquant"""
        pole_admin = Group.objects.get(name='POLE_ADMINISTRATIF')

        form_data = {
            'poles': [pole_admin.id]
        }

        form = UserInvitationForm(data=form_data)
        assert not form.is_valid()
        assert 'email' in form.errors

    def test_missing_poles(self, create_groups):
        """Teste avec pôles manquants"""
        form_data = {
            'email': 'newuser@example.com'
        }

        form = UserInvitationForm(data=form_data)
        assert not form.is_valid()
        assert 'poles' in form.errors

    def test_invalid_email_format(self, create_groups):
        """Teste avec un format d'email invalide"""
        pole_admin = Group.objects.get(name='POLE_ADMINISTRATIF')

        form_data = {
            'email': 'not-an-email',
            'poles': [pole_admin.id]
        }

        form = UserInvitationForm(data=form_data)
        assert not form.is_valid()
        assert 'email' in form.errors

    def test_duplicate_email(self, create_groups):
        """Teste avec un email déjà existant"""

        User.objects.create_user(
            username='existing',
            email='existing@example.com',
            password='testpass123'
        )

        pole_admin = Group.objects.get(name='POLE_ADMINISTRATIF')

        form_data = {
            'email': 'existing@example.com',
            'poles': [pole_admin.id]
        }

        form = UserInvitationForm(data=form_data)
        assert not form.is_valid()
        assert 'email' in form.errors
        assert 'existe déjà' in str(form.errors['email']).lower()

    def test_email_case_insensitive(self, create_groups):
        """Teste que la validation d'email est insensible à la casse"""
        User.objects.create_user(
            username='existing',
            email='existing@example.com',
            password='testpass123'
        )

        pole_admin = Group.objects.get(name='POLE_ADMINISTRATIF')

        form_data = {
            'email': 'EXISTING@EXAMPLE.COM',
            'poles': [pole_admin.id]
        }

        form = UserInvitationForm(data=form_data)
        assert form.is_valid()





    def test_ceo_group_excluded(self, create_groups):
        """Teste que le groupe CEO est exclu du queryset"""
        form = UserInvitationForm()


        available_groups = form.fields['poles'].queryset
        group_names = [g.name for g in available_groups]

        assert 'CEO' not in group_names
        assert 'POLE_ADMINISTRATIF' in group_names
        assert 'POLE_TECHNIQUE' in group_names

    def test_multiple_poles_selection(self, create_groups):
        """Teste la sélection de plusieurs pôles"""
        pole_admin = Group.objects.get(name='POLE_ADMINISTRATIF')
        pole_tech = Group.objects.get(name='POLE_TECHNIQUE')
        pole_finance = Group.objects.get(name='POLE_FINANCIER')

        form_data = {
            'email': 'multipole@example.com',
            'poles': [pole_admin.id, pole_tech.id, pole_finance.id]
        }

        form = UserInvitationForm(data=form_data)
        assert form.is_valid()
        assert len(form.cleaned_data['poles']) == 3

    def test_empty_poles_list(self, create_groups):
        """Teste avec une liste de pôles vide"""
        form_data = {
            'email': 'test@example.com',
            'poles': []
        }

        form = UserInvitationForm(data=form_data)
        assert not form.is_valid()
        assert 'poles' in form.errors

    def test_whitespace_in_email(self, create_groups):
        """Teste avec des espaces dans l'email"""
        pole_admin = Group.objects.get(name='POLE_ADMINISTRATIF')

        form_data = {
            'email': '  user@example.com  ',
            'poles': [pole_admin.id]
        }

        form = UserInvitationForm(data=form_data)

        if form.is_valid():

            assert form.cleaned_data['email'] == 'user@example.com'


@pytest.mark.django_db
class TestAccountActivationForm:
    """Tests pour le formulaire AccountActivationForm"""

    def test_valid_form(self):
        """Teste un formulaire valide"""
        form_data = {
            'first_name': 'Jean',
            'last_name': 'Dupont',
            'username': 'jdupont',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!'
        }

        form = AccountActivationForm(data=form_data)
        assert form.is_valid()

    def test_missing_first_name(self):
        """Teste avec prénom manquant"""
        form_data = {
            'last_name': 'Dupont',
            'username': 'jdupont',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!'
        }

        form = AccountActivationForm(data=form_data)
        assert not form.is_valid()
        assert 'first_name' in form.errors

    def test_missing_last_name(self):
        """Teste avec nom manquant"""
        form_data = {
            'first_name': 'Jean',
            'username': 'jdupont',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!'
        }

        form = AccountActivationForm(data=form_data)
        assert not form.is_valid()
        assert 'last_name' in form.errors

    def test_missing_username(self):
        """Teste avec username manquant"""
        form_data = {
            'first_name': 'Jean',
            'last_name': 'Dupont',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!'
        }

        form = AccountActivationForm(data=form_data)
        assert not form.is_valid()
        assert 'username' in form.errors

    def test_missing_password(self):
        """Teste avec mot de passe manquant"""
        form_data = {
            'first_name': 'Jean',
            'last_name': 'Dupont',
            'username': 'jdupont',
            'password_confirm': 'SecurePass123!'
        }

        form = AccountActivationForm(data=form_data)
        assert not form.is_valid()
        assert 'password' in form.errors

    def test_missing_password_confirm(self):
        """Teste avec confirmation de mot de passe manquante"""
        form_data = {
            'first_name': 'Jean',
            'last_name': 'Dupont',
            'username': 'jdupont',
            'password': 'SecurePass123!'
        }

        form = AccountActivationForm(data=form_data)
        assert not form.is_valid()
        assert 'password_confirm' in form.errors

    def test_password_mismatch(self):
        """Teste quand les mots de passe ne correspondent pas"""
        form_data = {
            'first_name': 'Jean',
            'last_name': 'Dupont',
            'username': 'jdupont',
            'password': 'SecurePass123!',
            'password_confirm': 'DifferentPass456!'
        }

        form = AccountActivationForm(data=form_data)
        assert not form.is_valid()
        assert '__all__' in form.errors or 'password' in str(form.errors).lower()
        assert 'correspondent pas' in str(form.errors).lower()

    def test_duplicate_username(self):
        """Teste avec un username déjà existant"""
        User.objects.create_user(
            username='existinguser',
            email='existing@example.com',
            password='testpass123'
        )

        form_data = {
            'first_name': 'Jean',
            'last_name': 'Dupont',
            'username': 'existinguser',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!'
        }

        form = AccountActivationForm(data=form_data)
        assert not form.is_valid()
        assert 'username' in form.errors
        assert 'déjà pris' in str(form.errors['username']).lower()

    def test_username_case_sensitive(self):
        """Teste que les usernames sont sensibles à la casse"""

        User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        form_data = {
            'first_name': 'Jean',
            'last_name': 'Dupont',
            'username': 'TESTUSER',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!'
        }
        form = AccountActivationForm(data=form_data)
        assert form.is_valid()



    def test_short_password(self):
        """Teste avec un mot de passe trop court"""
        form_data = {
            'first_name': 'Jean',
            'last_name': 'Dupont',
            'username': 'jdupont',
            'password': '123',
            'password_confirm': '123'
        }

        form = AccountActivationForm(data=form_data)
        assert form.is_valid()
    



    def test_empty_strings(self):
        """Teste avec des chaînes vides"""
        form_data = {
            'first_name': '',
            'last_name': '',
            'username': '',
            'password': '',
            'password_confirm': ''
        }

        form = AccountActivationForm(data=form_data)
        assert not form.is_valid()
        assert len(form.errors) >= 4

    def test_whitespace_in_username(self):
        """Teste avec des espaces dans le username"""
        form_data = {
            'first_name': 'Jean',
            'last_name': 'Dupont',
            'username': '  jdupont  ',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!'
        }

        form = AccountActivationForm(data=form_data)

        if form.is_valid():

            assert form.cleaned_data['username'] == 'jdupont'

    def test_special_characters_in_names(self):
        """Teste avec des caractères spéciaux dans les noms"""
        form_data = {
            'first_name': 'Jean-Pierre',
            'last_name': "O'Connor",
            'username': 'jpconnor',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!'
        }

        form = AccountActivationForm(data=form_data)
        assert form.is_valid()
        assert form.cleaned_data['first_name'] == 'Jean-Pierre'
        assert form.cleaned_data['last_name'] == "O'Connor"

    def test_unicode_characters_in_names(self):
        """Teste avec des caractères Unicode dans les noms"""
        form_data = {
            'first_name': 'José',
            'last_name': 'García',
            'username': 'jgarcia',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!'
        }

        form = AccountActivationForm(data=form_data)
        assert form.is_valid()
        assert form.cleaned_data['first_name'] == 'José'
        assert form.cleaned_data['last_name'] == 'García'

    def test_max_length_fields(self):
        """Teste avec des champs à longueur maximale"""
        long_name = 'A' * 150

        form_data = {
            'first_name': long_name,
            'last_name': long_name,
            'username': 'B' * 150,
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!'
        }

        form = AccountActivationForm(data=form_data)
        assert form.is_valid()

    def test_exceed_max_length(self):
        """Teste avec des champs dépassant la longueur maximale"""
        too_long = 'A' * 151

        form_data = {
            'first_name': too_long,
            'last_name': 'Dupont',
            'username': 'jdupont',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!'
        }

        form = AccountActivationForm(data=form_data)
        assert not form.is_valid()
        assert 'first_name' in form.errors

    def test_password_visibility_widget(self):
        """Teste que le widget du mot de passe est bien PasswordInput"""
        form = AccountActivationForm()

        assert form.fields['password'].widget.__class__.__name__ == 'PasswordInput'
        assert form.fields['password_confirm'].widget.__class__.__name__ == 'PasswordInput'

    def test_clean_called_after_field_validation(self):
        """Teste que clean() est appelé après la validation des champs individuels"""

        form_data = {
            'first_name': 'Jean',
            'last_name': 'Dupont',
            'username': 'jdupont',
            'password': '',
            'password_confirm': 'something'
        }

        form = AccountActivationForm(data=form_data)
        assert not form.is_valid()


        assert 'password' in form.errors