"""
OAuth2 utilities pour Microsoft Graph API
Gestion de l'authentification et des tokens d'accès
"""
import msal
import requests
from django.conf import settings
from .modelsadm import OAuthToken


def get_authorization_url():
    """
    Génère l'URL d'autorisation Microsoft OAuth2

    Returns:
        tuple: (auth_url, state)
    """
    app = msal.ConfidentialClientApplication(
        client_id=settings.MICROSOFT_CLIENT_ID,
        client_credential=settings.MICROSOFT_CLIENT_SECRET,
        authority=f"https://login.microsoftonline.com/{settings.MICROSOFT_TENANT_ID}"
    )

    auth_url = app.get_authorization_request_url(
        scopes=settings.MICROSOFT_SCOPES,
        redirect_uri=settings.MICROSOFT_REDIRECT_URI
    )

    # Extraire le state de l'URL pour validation ultérieure
    state = auth_url.split('state=')[1].split('&')[0] if 'state=' in auth_url else None

    return auth_url, state


def exchange_code_for_token(authorization_code):
    """
    Échange le code d'autorisation contre un access token et refresh token

    Args:
        authorization_code (str): Code d'autorisation reçu du callback

    Returns:
        dict: Token response contenant access_token, refresh_token, etc.

    Raises:
        Exception: Si l'échange échoue
    """
    app = msal.ConfidentialClientApplication(
        client_id=settings.MICROSOFT_CLIENT_ID,
        client_credential=settings.MICROSOFT_CLIENT_SECRET,
        authority=f"https://login.microsoftonline.com/{settings.MICROSOFT_TENANT_ID}"
    )

    result = app.acquire_token_by_authorization_code(
        code=authorization_code,
        scopes=settings.MICROSOFT_SCOPES,
        redirect_uri=settings.MICROSOFT_REDIRECT_URI
    )

    if "error" in result:
        error_description = result.get("error_description", result.get("error"))
        raise Exception(f"Erreur lors de l'échange du code: {error_description}")

    return result


def get_access_token(user):
    """
    Récupère un access token valide pour l'utilisateur
    Rafraîchit automatiquement le token si nécessaire

    Args:
        user (User): Utilisateur Django

    Returns:
        str: Access token valide

    Raises:
        Exception: Si aucun token n'existe ou si le rafraîchissement échoue
    """
    try:
        oauth_token = OAuthToken.objects.get(user=user)
    except OAuthToken.DoesNotExist:
        raise Exception("Aucun token OAuth trouvé pour cet utilisateur")

    # Vérifier si le token est encore valide (optionnel, MSAL gère le cache)
    # Pour simplifier, on tente toujours de rafraîchir via MSAL

    app = msal.ConfidentialClientApplication(
        client_id=settings.MICROSOFT_CLIENT_ID,
        client_credential=settings.MICROSOFT_CLIENT_SECRET,
        authority=f"https://login.microsoftonline.com/{settings.MICROSOFT_TENANT_ID}"
    )

    # Essayer d'acquérir un token silencieusement (cache)
    accounts = app.get_accounts()

    if accounts:
        result = app.acquire_token_silent(
            scopes=settings.MICROSOFT_SCOPES,
            account=accounts[0]
        )
    else:
        result = None

    # Si échec, utiliser le refresh token
    if not result or "access_token" not in result:
        result = app.acquire_token_by_refresh_token(
            refresh_token=oauth_token.refresh_token,
            scopes=settings.MICROSOFT_SCOPES
        )

        if "error" in result:
            error_description = result.get("error_description", result.get("error"))
            raise Exception(f"Erreur lors du rafraîchissement du token: {error_description}")

        # Mettre à jour le token en base de données
        oauth_token.access_token = result['access_token']
        if 'refresh_token' in result:
            oauth_token.refresh_token = result['refresh_token']
        oauth_token.save()

    return result['access_token']


def get_user_email(access_token):
    """
    Récupère l'adresse email de l'utilisateur connecté

    Args:
        access_token (str): Access token Microsoft

    Returns:
        str: Adresse email de l'utilisateur

    Raises:
        Exception: Si la requête échoue
    """
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    response = requests.get(
        'https://graph.microsoft.com/v1.0/me',
        headers=headers
    )

    if response.status_code != 200:
        raise Exception(f"Erreur lors de la récupération du profil: {response.text}")

    user_data = response.json()
    return user_data.get('mail') or user_data.get('userPrincipalName')


def revoke_token(user):
    """
    Révoque le token OAuth de l'utilisateur (déconnexion)

    Args:
        user (User): Utilisateur Django

    Returns:
        bool: True si succès, False sinon
    """
    try:
        oauth_token = OAuthToken.objects.get(user=user)
        oauth_token.delete()
        return True
    except OAuthToken.DoesNotExist:
        return False