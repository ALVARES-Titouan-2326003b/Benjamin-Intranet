"""
Vues pour gérer le flux OAuth2 Gmail
VERSION CORRIGÉE : Redirections vers /administratif/ au lieu de namespace
"""
from django.shortcuts import redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from management.modelsadm import OAuthToken
from management.oauth_utils import (
    get_authorization_url,
    exchange_code_for_tokens
)


@login_required
def initiate_oauth(request):
    """
    Vue pour initier le flux OAuth2
    Redirige l'utilisateur vers Google pour autoriser l'accès

    URL : /oauth/gmail/
    """

    redirect_uri = request.build_absolute_uri('/oauth/callback/')


    authorization_url, state = get_authorization_url(redirect_uri)


    request.session['oauth_state'] = state

    print(f"\n{'='*60}")
    print(f"🚀 Initiation OAuth pour {request.user.username}")
    print(f"   Redirect URI: {redirect_uri}")
    print(f"   State: {state}")
    print(f"{'='*60}\n")


    return redirect(authorization_url)


@login_required
def oauth_callback(request):
    """
    Vue de callback OAuth2
    Reçoit le code d'autorisation de Google et l'échange contre des tokens

    URL : /oauth/callback/?code=XXX&state=YYY
    """
    code = request.GET.get('code')
    state = request.GET.get('state')
    error = request.GET.get('error')

    print(f"\n{'='*60}")
    print(f"📥 Callback OAuth pour {request.user.username}")
    print(f"   Code: {code[:20]}..." if code else "   Code: None")
    print(f"   State: {state}")
    print(f"   Error: {error}")
    print(f"{'='*60}\n")

    if error:
        messages.error(request, f"Erreur OAuth : {error}")
        print(f"❌ Erreur OAuth : {error}")
        return redirect('/administratif/')  # ✅ CORRECTION : URL directe

    if not code:
        messages.error(request, "Code d'autorisation manquant")
        print(f"❌ Code manquant")
        return redirect('/administratif/')  # ✅ CORRECTION : URL directe

    session_state = request.session.get('oauth_state')
    if state != session_state:
        messages.error(request, "État OAuth invalide (possible attaque CSRF)")
        print(f"❌ State invalide : {state} != {session_state}")
        return redirect('/administratif/')  # ✅ CORRECTION : URL directe

    try:

        redirect_uri = request.build_absolute_uri('/oauth/callback/')

        print(f"Échange du code contre des tokens...")
        tokens = exchange_code_for_tokens(code, redirect_uri)

        print(f"Tokens reçus !")
        print(f"   Email: {tokens['email']}")
        print(f"   Access token: {tokens['access_token'][:20]}...")
        print(f"   Refresh token: {'OUI' if tokens['refresh_token'] else 'NON'}")
        print(f"   Expiration: {tokens['token_expiry']}")


        if tokens['email'] != request.user.email:
            messages.warning(
                request,
                f"⚠L'email autorisé ({tokens['email']}) ne correspond pas à votre compte ({request.user.email}). "
                f"Mise à jour de votre email..."
            )
            request.user.email = tokens['email']
            request.user.save()

        oauth_token, created = OAuthToken.objects.update_or_create(
            user=request.user,
            defaults={
                'provider': 'google',
                'email': tokens['email'],
                'access_token': tokens['access_token'],
                'refresh_token': tokens['refresh_token'],
                'token_expiry': tokens['token_expiry']
            }
        )

        if created:
            messages.success(
                request,
                f"✅ Boîte mail {tokens['email']} synchronisée avec succès !"
            )
            print(f"✅ Nouveau token créé pour {request.user.username}")
        else:
            messages.success(
                request,
                f"✅ Boîte mail {tokens['email']} mise à jour avec succès !"
            )
            print(f"Token mis à jour pour {request.user.username}")

        if 'oauth_state' in request.session:
            del request.session['oauth_state']

        print(f"{'='*60}\n")

        return redirect('/administratif/')  # ✅ CORRECTION : URL directe

    except Exception as e:
        messages.error(request, f"❌ Erreur lors de l'authentification : {str(e)}")
        print(f"❌ Erreur : {e}")
        import traceback
        traceback.print_exc()
        return redirect('/administratif/')  # ✅ CORRECTION : URL directe


@login_required
@require_http_methods(["POST"])
def revoke_oauth(request):
    """
    Révoque l'accès OAuth (supprime les tokens)

    URL : /oauth/revoke/
    Method : POST
    """
    try:
        oauth_token = OAuthToken.objects.get(user=request.user)
        email = oauth_token.email
        oauth_token.delete()

        messages.success(
            request,
            f"✅ Accès à la boîte mail {email} révoqué avec succès."
        )
        print(f"🗑️  Token OAuth supprimé pour {request.user.username}")

        return JsonResponse({'success': True})

    except OAuthToken.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Aucune boîte mail synchronisée'
        }, status=404)


@login_required
def oauth_status(request):
    """
    Vérifie le statut OAuth de l'utilisateur

    URL : /oauth/status/
    Returns : JSON avec les infos de synchronisation
    """
    try:
        oauth_token = OAuthToken.objects.get(user=request.user)

        return JsonResponse({
            'synchronized': True,
            'email': oauth_token.email,
            'provider': oauth_token.provider,
            'token_expired': oauth_token.is_token_expired(),
            'last_update': oauth_token.updated_at.isoformat()
        })

    except OAuthToken.DoesNotExist:
        return JsonResponse({
            'synchronized': False
        })