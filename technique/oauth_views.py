from django.shortcuts import redirect
from django.http import JsonResponse
import traceback

from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from management.models import OAuthToken
from management.oauth_utils import (
    get_authorization_url,
    exchange_code_for_tokens
)

# URL de redirection par défaut (pôle administratif)
DEFAULT_REDIRECT = '/administratif/'

# Liste blanche des redirections autorisées après OAuth
ALLOWED_REDIRECTS = [
    '/administratif/',
    '/pole-technique/email/',
]


@login_required
def initiate_oauth(request):
    """
    Initie le flux OAuth2.
    Stocke l'URL de retour dans la session si elle est dans la liste blanche.

    URL : /oauth/gmail/
    URL technique : /oauth/gmail/?next=/pole-technique/email/
    """
    # Lecture et validation du paramètre 'next'
    next_url = request.GET.get('next', DEFAULT_REDIRECT)
    if next_url not in ALLOWED_REDIRECTS:
        next_url = DEFAULT_REDIRECT

    request.session['oauth_next'] = next_url

    redirect_uri = request.build_absolute_uri('/oauth/callback/')
    authorization_url, state = get_authorization_url(redirect_uri)
    request.session['oauth_state'] = state

    print(f"\n{'='*60}")
    print(f"   Initiation OAuth pour {request.user.username}")
    print(f"   Redirect URI: {redirect_uri}")
    print(f"   Retour après auth : {next_url}")
    print(f"{'='*60}\n")

    return redirect(authorization_url)


@login_required
def oauth_callback(request):
    """
    Callback OAuth2 — redirige vers l'URL stockée en session (ou /administratif/).

    URL : /oauth/callback/?code=XXX&state=YYY
    """
    code  = request.GET.get('code')
    state = request.GET.get('state')
    error = request.GET.get('error')

    # Récupération de l'URL de retour (avec nettoyage)
    next_url = request.session.pop('oauth_next', DEFAULT_REDIRECT)
    if next_url not in ALLOWED_REDIRECTS:
        next_url = DEFAULT_REDIRECT

    print(f"\n{'='*60}")
    print(f"   Callback OAuth pour {request.user.username}")
    print(f"   Code: {code[:20]}..." if code else "   Code: None")
    print(f"   Retour prévu : {next_url}")
    print(f"{'='*60}\n")

    if error:
        messages.error(request, f"Erreur OAuth : {error}")
        return redirect(next_url)

    if not code:
        messages.error(request, "Code d'autorisation manquant")
        return redirect(next_url)

    session_state = request.session.get('oauth_state')
    if state != session_state:
        messages.error(request, "État OAuth invalide (possible attaque CSRF)")
        return redirect(next_url)

    try:
        redirect_uri = request.build_absolute_uri('/oauth/callback/')
        tokens = exchange_code_for_tokens(code, redirect_uri)

        print(f"   Email: {tokens['email']}")
        print(f"   Refresh token: {'OUI' if tokens['refresh_token'] else 'NON'}")

        if tokens['email'] != request.user.email:
            messages.warning(
                request,
                f"L'email autorisé ({tokens['email']}) ne correspond pas à votre compte "
                f"({request.user.email}). Mise à jour de votre email..."
            )
            request.user.email = tokens['email']
            request.user.save()

        _, created = OAuthToken.objects.update_or_create(
            user=request.user,
            defaults={
                'provider':      'google',
                'email':         tokens['email'],
                'access_token':  tokens['access_token'],
                'refresh_token': tokens['refresh_token'],
                'token_expiry':  tokens['token_expiry'],
            }
        )

        messages.success(
            request,
            f"Boîte mail {tokens['email']} {'synchronisée' if created else 'mise à jour'} avec succès !"
        )

        if 'oauth_state' in request.session:
            del request.session['oauth_state']

        return redirect(next_url)

    except Exception as e:
        messages.error(request, f"Erreur lors de l'authentification : {str(e)}")
        traceback.print_exc()
        return redirect(next_url)


@login_required
@require_http_methods(["POST"])
def revoke_oauth(request):
    """
    Révoque l'accès OAuth (supprime les tokens).
    URL : /oauth/revoke/
    """
    try:
        oauth_token = OAuthToken.objects.get(user=request.user)
        email = oauth_token.email
        oauth_token.delete()

        messages.success(request, f"Accès à la boîte mail {email} révoqué avec succès.")
        print(f"Token OAuth supprimé pour {request.user.username}")

        return JsonResponse({'success': True})

    except OAuthToken.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Aucune boîte mail synchronisée'}, status=404)


@login_required
def oauth_status(request):
    """
    Statut OAuth de l'utilisateur.
    URL : /oauth/status/
    """
    try:
        oauth_token = OAuthToken.objects.get(user=request.user)
        return JsonResponse({
            'synchronized':  True,
            'email':         oauth_token.email,
            'provider':      oauth_token.provider,
            'token_expired': oauth_token.is_token_expired(),
            'last_update':   oauth_token.updated_at.isoformat(),
        })
    except OAuthToken.DoesNotExist:
        return JsonResponse({'synchronized': False})