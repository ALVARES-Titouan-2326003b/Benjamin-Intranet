from django.shortcuts import redirect
from django.http import JsonResponse

from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
import logging
from management.models import OAuthToken
from management.oauth_utils import (
    get_authorization_url,
    exchange_code_for_tokens,
)

# Destination par défaut (inchangée pour le pôle administratif)
DEFAULT_REDIRECT = '/administratif/'
logger = logging.getLogger(__name__)

# Seules ces URLs sont autorisées comme destination post-OAuth (sécurité)
ALLOWED_REDIRECTS = [
    '/administratif/',
    '/pole-technique/email/',
]


@login_required
def initiate_oauth(request):
    """
    Initie le flux OAuth2 Microsoft.
    Stocke l'URL de retour dans la session avant de partir vers Microsoft.

    URL : /oauth/microsoft/
    URL pôle technique : /oauth/microsoft/?next=/pole-technique/email/
    """
    # Lire et valider le paramètre next
    next_url = request.GET.get('next', DEFAULT_REDIRECT)
    if next_url not in ALLOWED_REDIRECTS:
        next_url = DEFAULT_REDIRECT

    # Stocker en session pour le récupérer dans le callback
    request.session['oauth_next'] = next_url
    request.session.modified = True  # forcer la sauvegarde de la session

    redirect_uri = request.build_absolute_uri('/oauth/callback/')
    authorization_url, state = get_authorization_url(redirect_uri)
    request.session['oauth_state'] = state

    logger.info("Initiation OAuth Microsoft pour user_id=%s", request.user.pk)

    return redirect(authorization_url)


@login_required
def initiate_gmail_oauth(request):
    """
    Initie le flux OAuth2 Google/Gmail.
    Stocke l'URL de retour dans la session avant de partir vers Google.

    URL : /oauth/gmail/
    URL pôle technique : /oauth/gmail/?next=/pole-technique/email/
    """
    # Lire et valider le paramètre next
    next_url = request.GET.get('next', DEFAULT_REDIRECT)
    if next_url not in ALLOWED_REDIRECTS:
        next_url = DEFAULT_REDIRECT

    # Stocker en session pour le récupérer dans le callback
    request.session['oauth_next'] = next_url
    request.session['oauth_provider'] = 'google'
    request.session.modified = True  # forcer la sauvegarde de la session

    redirect_uri = request.build_absolute_uri('/oauth/callback/')
    authorization_url, state = get_authorization_url(redirect_uri, provider="google")
    request.session['oauth_state'] = state

    logger.info("Initiation OAuth Gmail pour user_id=%s", request.user.pk)

    return redirect(authorization_url)


@login_required
def oauth_callback(request):
    """
    Callback OAuth2 — échange le code et redirige vers next_url.

    URL : /oauth/callback/?code=XXX&state=YYY
    """
    code  = request.GET.get('code')
    state = request.GET.get('state')
    error = request.GET.get('error')

    # Récupérer la destination et le provider stockés en session (avec nettoyage)
    next_url = request.session.pop('oauth_next', DEFAULT_REDIRECT)
    provider = request.session.pop('oauth_provider', 'microsoft')
    if next_url not in ALLOWED_REDIRECTS:
        next_url = DEFAULT_REDIRECT

    logger.info("Callback OAuth %s pour user_id=%s", provider, request.user.pk)

    if error:
        messages.error(request, f"Erreur OAuth : {error}")
        return redirect(next_url)

    if not code:
        messages.error(request, "Code d'autorisation manquant.")
        return redirect(next_url)

    session_state = request.session.get('oauth_state')
    if state != session_state:
        messages.error(request, "État OAuth invalide (possible attaque CSRF).")
        logger.warning("État OAuth invalide pour user_id=%s", request.user.pk)
        return redirect(next_url)

    try:
        redirect_uri = request.build_absolute_uri('/oauth/callback/')
        tokens = exchange_code_for_tokens(code, redirect_uri, provider=provider)

        if tokens['email'] != request.user.email:
            messages.warning(
                request,
                f"L'email autorisé ({tokens['email']}) ne correspond pas à votre compte "
                f"({request.user.email}). Mise à jour de votre email..."
            )
            request.user.email = tokens['email']
            request.user.save()

        existing_token = OAuthToken.objects.filter(user=request.user).first()
        refresh_token = tokens["refresh_token"] or (
            existing_token.refresh_token if existing_token else ""
        )
        _, created = OAuthToken.objects.update_or_create(
            user=request.user,
            defaults={
                'provider':      provider,
                'email':         tokens['email'],
                'access_token':  tokens['access_token'],
                'refresh_token': refresh_token,
                'token_expiry':  tokens['token_expiry'],
            }
        )

        action = "synchronisée" if created else "mise à jour"
        messages.success(request, f"Boîte mail {tokens['email']} {action} avec succès !")
        logger.info("Jeton OAuth enregistré pour user_id=%s", request.user.pk)

        if 'oauth_state' in request.session:
            del request.session['oauth_state']

        return redirect(next_url)   # ← redirige vers /administratif/ OU /pole-technique/email/

    except Exception:
        messages.error(request, "Erreur lors de l'authentification OAuth.")
        logger.exception("Échec du callback OAuth pour user_id=%s", request.user.pk)
        return redirect(next_url)


@login_required
@require_http_methods(["POST"])
def revoke_oauth(request):
    """Révoque l'accès OAuth. URL : /oauth/revoke/"""
    try:
        oauth_token = OAuthToken.objects.get(user=request.user, provider="google")
        email = oauth_token.email
        oauth_token.delete()
        messages.success(request, f"Accès à la boîte mail {email} révoqué avec succès.")
        logger.info("Jeton OAuth révoqué pour user_id=%s", request.user.pk)
        return JsonResponse({'success': True})

    except OAuthToken.DoesNotExist:
        return JsonResponse(
            {'success': False, 'message': 'Aucune boîte mail synchronisée'},
            status=404
        )


@login_required
def oauth_status(request):
    """Statut OAuth de l'utilisateur. URL : /oauth/status/"""
    try:
        oauth_token = OAuthToken.objects.get(user=request.user, provider="google")
        return JsonResponse({
            'synchronized':  True,
            'email':         oauth_token.email,
            'provider':      oauth_token.provider,
            'token_expired': oauth_token.is_token_expired(),
            'last_update':   oauth_token.updated_at.isoformat(),
        })
    except OAuthToken.DoesNotExist:
        return JsonResponse({'synchronized': False})
