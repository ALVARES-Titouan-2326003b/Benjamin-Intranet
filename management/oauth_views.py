"""
Vues pour gerer le flux OAuth2 Microsoft Graph API
"""
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .oauth_utils import (
    get_authorization_url,
    exchange_code_for_token,
    get_user_email,
    revoke_token
)
from .modelsadm import OAuthToken


@login_required
def initiate_oauth(request):
    """
    Vue pour initier le flux OAuth2 Microsoft
    Redirige l'utilisateur vers la page de connexion Microsoft

    URL : /oauth/microsoft/
    """
    try:
        # Generer l'URL d'autorisation Microsoft
        authorization_url, state = get_authorization_url()

        # SOLUTION 2 : Sauvegarder explicitement la session
        request.session['oauth_state'] = state
        request.session.modified = True  # Marquer la session comme modifiee
        request.session.save()           # Forcer la sauvegarde

        print(f"\n{'='*60}")
        print(f"Initiation OAuth Microsoft pour {request.user.username}")
        print(f"   State genere: {state}")
        print(f"   Session sauvegardee: OUI")
        print(f"   Session key: {request.session.session_key}")
        print(f"   Redirection vers: {authorization_url[:80]}...")
        print(f"{'='*60}\n")

        # Rediriger vers Microsoft
        return redirect(authorization_url)

    except Exception as e:
        messages.error(request, f"Erreur lors de l'initiation OAuth: {str(e)}")
        print(f"Erreur initiate_oauth: {e}")
        import traceback
        traceback.print_exc()
        return redirect('/administratif/')


def oauth_callback(request):
    """
    Vue de callback OAuth2 Microsoft
    Recoit le code d'autorisation de Microsoft et l'echange contre des tokens

    URL : /oauth/callback/?code=XXX&state=YYY

    Note : Pas de @login_required car Microsoft redirige ici
    La verification d'authentification est faite manuellement
    """
    # Verification manuelle de l'authentification
    if not request.user.is_authenticated:
        messages.error(
            request,
            "Votre session a expire. Veuillez vous reconnecter puis relancer la synchronisation."
        )
        print(f"\n[ERREUR] Callback OAuth : Utilisateur non authentifie")
        print(f"   Session key: {request.session.session_key}")
        print(f"   User: {request.user}\n")
        # Rediriger vers la page de login avec next parameter
        return redirect('/account/login/?next=/administratif/')

    # Recuperer les parametres du callback
    code = request.GET.get('code')
    state = request.GET.get('state')
    error = request.GET.get('error')

    print(f"\n{'='*60}")
    print(f"Callback OAuth Microsoft pour {request.user.username}")
    print(f"   Code: {code[:20]}..." if code else "   Code: None")
    print(f"   State recu: {state}")
    print(f"   State session: {request.session.get('oauth_state')}")
    print(f"   Error: {error}")
    print(f"   Session key: {request.session.session_key}")
    print(f"{'='*60}\n")

    # Gerer les erreurs OAuth
    if error:
        error_description = request.GET.get('error_description', 'Erreur inconnue')
        messages.error(request, f"Erreur OAuth : {error_description}")
        print(f"Erreur OAuth : {error} - {error_description}")
        return redirect('/administratif/')

    # Verifier que le code est present
    if not code:
        messages.error(request, "Code d'autorisation manquant")
        print(f"Code d'autorisation manquant")
        return redirect('/administratif/')

    # Verifier le state pour prevenir les attaques CSRF
    session_state = request.session.get('oauth_state')
    if state and session_state and state != session_state:
        messages.error(request, "Etat OAuth invalide (possible attaque CSRF)")
        print(f"State invalide : recu={state}, session={session_state}")
        return redirect('/administratif/')

    try:
        # Echanger le code contre des tokens
        print(f"Echange du code contre des tokens...")
        token_response = exchange_code_for_token(code)

        # Extraire les tokens
        access_token = token_response.get('access_token')
        refresh_token = token_response.get('refresh_token')

        if not access_token or not refresh_token:
            raise Exception("Tokens manquants dans la reponse Microsoft")

        print(f"Tokens recus avec succes !")
        print(f"   Access token: {access_token[:20]}...")
        print(f"   Refresh token: {'OUI' if refresh_token else 'NON'}")

        # Recuperer l'email de l'utilisateur Microsoft
        user_email = get_user_email(access_token)
        print(f"   Email Microsoft: {user_email}")
        print(f"   Email Django: {request.user.email}")

        # Verifier la correspondance des emails
        if user_email != request.user.email:
            messages.warning(
                request,
                f"L'email autorise ({user_email}) ne correspond pas a votre compte ({request.user.email}). "
                f"Mise a jour de votre email..."
            )
            request.user.email = user_email
            request.user.save()
            print(f"   Email mis a jour : {request.user.email}")

        # Sauvegarder ou mettre a jour le token OAuth
        oauth_token, created = OAuthToken.objects.update_or_create(
            user=request.user,
            defaults={
                'email': user_email,
                'access_token': access_token,
                'refresh_token': refresh_token
            }
        )

        # Message de succes
        if created:
            messages.success(
                request,
                f"Boite mail {user_email} synchronisee avec succes !"
            )
            print(f"Nouveau token OAuth cree pour {request.user.username}")
        else:
            messages.success(
                request,
                f"Boite mail {user_email} mise a jour avec succes !"
            )
            print(f"Token OAuth mis a jour pour {request.user.username}")

        # Nettoyer le state de la session
        if 'oauth_state' in request.session:
            del request.session['oauth_state']
            print(f"   State supprime de la session")

        print(f"{'='*60}\n")

        # Rediriger vers la page administrative
        return redirect('/administratif/')

    except Exception as e:
        messages.error(request, f"Erreur lors de l'authentification : {str(e)}")
        print(f"\nErreur oauth_callback: {e}")
        import traceback
        traceback.print_exc()
        return redirect('/administratif/')


@login_required
@require_http_methods(["POST"])
def revoke_oauth(request):
    """
    Vue pour revoquer l'acces OAuth
    Supprime les tokens stockes et revoque l'acces sur Microsoft

    URL : /oauth/revoke/
    Method : POST
    """
    try:
        # Recuperer le token OAuth de l'utilisateur
        oauth_token = OAuthToken.objects.get(user=request.user)

        print(f"\n{'='*60}")
        print(f"Revocation OAuth pour {request.user.username}")
        print(f"   Email: {oauth_token.email}")
        print(f"{'='*60}\n")

        # Revoquer le token sur Microsoft (optionnel)
        try:
            revoke_token(oauth_token.refresh_token)
            print(f"   Token revoque sur Microsoft: OUI")
        except Exception as e:
            print(f"   Erreur revocation Microsoft: {e}")
            # Continue meme si la revocation Microsoft echoue

        # Supprimer le token de la base de donnees
        oauth_token.delete()
        print(f"   Token supprime de la base: OUI")

        messages.success(request, "Acces a la boite mail revoque avec succes")
        print(f"{'='*60}\n")

        return JsonResponse({
            'success': True,
            'message': 'Acces revoque avec succes'
        })

    except OAuthToken.DoesNotExist:
        print(f"\nAucun token OAuth trouve pour {request.user.username}")
        return JsonResponse({
            'success': False,
            'message': 'Aucun acces OAuth a revoquer'
        }, status=404)

    except Exception as e:
        print(f"\nErreur revoke_oauth: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': f'Erreur lors de la revocation : {str(e)}'
        }, status=500)


def oauth_status(request):
    """
    Verifie le statut OAuth de l'utilisateur
    Retourne JSON avec les informations de synchronisation

    URL : /oauth/status/
    Returns : JSON

    Note : Pas de @login_required car doit retourner JSON meme si non connecte
    """
    # Si pas connecte, retourner directement synchronized: false
    if not request.user.is_authenticated:
        return JsonResponse({
            'synchronized': False
        })

    try:
        # Recuperer le token OAuth de l'utilisateur
        oauth_token = OAuthToken.objects.get(user=request.user)

        return JsonResponse({
            'synchronized': True,
            'email': oauth_token.email,
            'provider': 'microsoft',
            'last_update': oauth_token.updated_at.isoformat() if hasattr(oauth_token, 'updated_at') else None
        })

    except OAuthToken.DoesNotExist:
        return JsonResponse({
            'synchronized': False
        })

    except Exception as e:
        print(f"Erreur oauth_status: {e}")
        return JsonResponse({
            'synchronized': False,
            'error': str(e)
        }, status=500)