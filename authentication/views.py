from two_factor.views import LoginView
from django.shortcuts import redirect, render
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User, Group
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings
from .forms import UserInvitationForm, AccountActivationForm
from django_otp.plugins.otp_email.models import EmailDevice


class CustomLoginView(LoginView):
    """Représente une page de connexion personnalisée."""
    def post(self, *args, **kwargs):
        # Vérifier si le bouton renvoyer est cliqué
        if 'resend_code' in self.request.POST:
            try:
                # Vérifier si on est à l'étape du token
                if self.storage.current_step == 'token':
                    # On vérifie la présence d'un user
                    user_pk = self.storage.data.get('user_pk')
                    
                    if user_pk:
                         from django.contrib.auth import get_user_model
                         User = get_user_model()
                         user = User.objects.get(pk=user_pk)
                    else:
                        user = None

                    if user:
                        # On vérifie la présence d'un appareil
                        for device in user.phonedevice_set.all():
                             if device.name == 'default':
                                 device.generate_challenge()
                                 messages.success(self.request, _("Un nouveau code a été envoyé."))
                                 break
                        else:
                            # Si aucun appreil trouvé, on envoie sur le premier
                            devices = user.phonedevice_set.all()
                            if devices.exists():
                                devices[0].generate_challenge()
                                messages.success(self.request, _("Un nouveau code a été envoyé."))

            except Exception:
                messages.error(self.request, _("Erreur lors de l'envoi du code."))

            #Empeche la redirection en boucle
            return self.render_goto_step('token')

        return super().post(*args, **kwargs)

# --- GESTION DES COMPTES (SUPERUSER) ---

@login_required
@user_passes_test(lambda u: u.is_superuser)
def user_management_view(request):
    """Tableau de bord de gestion des utilisateurs."""
    users = User.objects.all().order_by('-date_joined')
    return render(request, 'authentication/user_management.html', {'users': users})

@login_required
@user_passes_test(lambda u: u.is_superuser)
@login_required
@user_passes_test(lambda u: u.is_superuser)
def toggle_user_active_status_view(request, user_id):
    """Active ou désactive un utilisateur avec gestion hiérarchique des droits."""
    if request.method == 'POST':
        try:
            target_user = User.objects.get(pk=user_id)
            actor = request.user
            
            # Vérifications des rôles
            is_actor_ceo = actor.groups.filter(name="CEO").exists()
            is_target_ceo = target_user.groups.filter(name="CEO").exists()
            is_target_superuser = target_user.is_superuser

            # Sécurité de base : ne pas se désactiver soi-même
            if target_user == actor:
                messages.error(request, "Vous ne pouvez pas révoquer votre propre accès.")
                return redirect('authentication:user_management')

            # Logique hiérarchique
            # 1. Le CEO peut tout faire (sauf se révoquer lui-même, géré au-dessus)
            if is_actor_ceo:
                can_revoke = True
            
            # 2. Un Superuser (non CEO) ne peut PAS toucher au CEO ni aux autres Superusers
            else:
                if is_target_ceo or is_target_superuser:
                    can_revoke = False
                else:
                    can_revoke = True

            if can_revoke:
                target_user.is_active = not target_user.is_active
                target_user.save()
                status = "réactivé" if target_user.is_active else "révoqué"
                messages.success(request, f"L'accès de {target_user.email} a été {status}.")
            else:
                messages.error(request, "Vous n'avez pas les droits suffisants pour modifier cet utilisateur (Hiérarchie supérieure ou égale).")

        except User.DoesNotExist:
            messages.error(request, "Utilisateur introuvable.")
            
    return redirect('authentication:user_management')

@login_required
@user_passes_test(lambda u: u.is_superuser)
def invite_user_view(request):
    """Vue pour inviter un nouvel utilisateur."""
    if request.method == 'POST':
        form = UserInvitationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            poles = form.cleaned_data['poles']
            
            # Créer un utilisateur inactif avec un username temporaire (l'email)
            # On utilise l'email comme username temporaire car il est unique
            user = User.objects.create_user(username=email, email=email, is_active=False)
            user.groups.set(poles)
            user.save()
            
            # Générer le lien d'activation avec Token sécurisé
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Lien: /auth/activate/<uid>/<token>/
            # On suppose que l'URL sera montée sous /auth/ ou similaire. On utilisera 'authentication:activate'
            activation_link = request.build_absolute_uri(
                reverse('authentication:activate', kwargs={'uidb64': uid, 'token': token})
            )
            
            # 3. Envoyer l'email
            subject = "Activation de votre compte Intranet - Benjamin Immobilier"
            message = f"""Bonjour,

Un compte a été créé pour vous sur l'Intranet Benjamin Immobilier.

Pour finaliser votre inscription (choisir votre nom d'utilisateur et mot de passe), cliquez sur le lien suivant (valable 48h) :
{activation_link}

Si vous n'êtes pas à l'origine de cette demande, ignorez cet email.

Cordialement,
L'équipe Benjamin Immobilier
"""
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])
            
            messages.success(request, f"Invitation envoyée à {email}.")
            return redirect('authentication:user_management')
    else:
        form = UserInvitationForm()
    
    return render(request, 'authentication/invite_user.html', {'form': form})

def activate_account_view(request, uidb64, token):
    """Vue publique (mais protégée par token) pour activer son compte."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = AccountActivationForm(request.POST)
            if form.is_valid():
                new_username = form.cleaned_data['username']
                password = form.cleaned_data['password']
                first_name = form.cleaned_data['first_name']
                last_name = form.cleaned_data['last_name']
                
                # Mise à jour de l'utilisateur
                user.username = new_username
                user.first_name = first_name
                user.last_name = last_name
                user.set_password(password)
                user.is_active = True
                user.save()

                # On crée un device Email par défaut pour l'utilisateur
                device, created = EmailDevice.objects.get_or_create(
                    user=user, 
                    name='default', 
                    defaults={'email': user.email, 'confirmed': True}
                )
                # Si le device existait déjà mais avec un mauvais email, on le met à jour
                if not created and device.email != user.email:
                    device.email = user.email
                    device.save()
                
                messages.success(request, "Votre compte est activé avec succès ! (2FA activé par Email)")
                return redirect('two_factor:login')
        else:
            form = AccountActivationForm()
        
        return render(request, 'authentication/activate_account.html', {'form': form, 'valid_link': True})
    else:
        return render(request, 'authentication/activate_account.html', {'valid_link': False})
 
