"""
Utilitaires OAuth2 pour l'authentification Gmail
"""
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from django.utils import timezone
from datetime import timedelta
import os
from email.mime.text import MIMEText

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify',
]


def get_oauth_flow(redirect_uri):
    """
    Crée le flux OAuth2 pour l'authentification Google

    Args:
        redirect_uri (str): URL de callback (ex: http://localhost:8000/oauth/callback/)

    Returns:
        Flow: Objet Flow pour gérer l'authentification
    """
    client_config = {
        "web": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri]
        }
    }

    flow = Flow.from_client_config(
        client_config=client_config,
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )

    return flow


def get_authorization_url(redirect_uri):
    """
    Génère l'URL d'autorisation Google OAuth2

    Args:
        redirect_uri (str): URL de callback

    Returns:
        tuple: (authorization_url, state)
    """
    flow = get_oauth_flow(redirect_uri)

    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )

    return authorization_url, state


def exchange_code_for_tokens(code, redirect_uri):
    """
    Échange le code d'autorisation contre des tokens

    Args:
        code (str): Code d'autorisation reçu depuis Google
        redirect_uri (str): URL de callback

    Returns:
        dict: {
            'access_token': str,
            'refresh_token': str,
            'token_expiry': datetime,
            'email': str
        }
    """
    flow = get_oauth_flow(redirect_uri)
    flow.fetch_token(code=code)

    credentials = flow.credentials


    service = build('gmail', 'v1', credentials=credentials)
    profile = service.users().getProfile(userId='me').execute()
    user_email = profile['emailAddress']


    token_expiry = timezone.now() + timedelta(seconds=credentials.expiry.timestamp() - timezone.now().timestamp())

    return {
        'access_token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_expiry': token_expiry,
        'email': user_email
    }


def refresh_access_token(refresh_token):
    """
    Renouvelle l'access_token avec le refresh_token

    Args:
        refresh_token (str): Refresh token stocké en BD

    Returns:
        dict: {
            'access_token': str,
            'token_expiry': datetime
        }
    """
    from google.auth.transport.requests import Request

    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        scopes=SCOPES
    )


    credentials.refresh(Request())


    token_expiry = timezone.now() + timedelta(seconds=3600)  # 1 heure

    return {
        'access_token': credentials.token,
        'token_expiry': token_expiry
    }


def get_valid_credentials(oauth_token):
    """
    Récupère des credentials valides, les renouvelle si nécessaire

    Args:
        oauth_token (OAuthToken): Instance du modèle OAuthToken

    Returns:
        Credentials: Credentials Google valides
    """
    if oauth_token.is_token_expired():
        print(f"Token expiré pour {oauth_token.user.username}, renouvellement...")

        new_tokens = refresh_access_token(oauth_token.refresh_token)

        oauth_token.access_token = new_tokens['access_token']
        oauth_token.token_expiry = new_tokens['token_expiry']
        oauth_token.save()

        print(f"Token renouvelé pour {oauth_token.user.username}")

    credentials = Credentials(
        token=oauth_token.access_token,
        refresh_token=oauth_token.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        scopes=SCOPES
    )

    return credentials


def get_gmail_service(user):
    """
    Crée un service Gmail API pour l'utilisateur

    Args:
        user (User): Utilisateur Django

    Returns:
        Resource: Service Gmail API

    Raises:
        ValueError: Si l'utilisateur n'a pas de token OAuth
    """
    from management.models import OAuthToken

    try:
        oauth_token = OAuthToken.objects.get(user=user.id)
    except OAuthToken.DoesNotExist:
        raise ValueError(
            f"L'utilisateur {user.username} n'a pas synchronisé sa boîte mail. "
            f"Cliquez sur 'Synchroniser boite mail' pour autoriser l'accès."
        )

    credentials = get_valid_credentials(oauth_token)
    service = build('gmail', 'v1', credentials=credentials)

    return service

def send_email_via_gmail_api(user, to_email, subject, message_text):
    """
    Envoie un email via Gmail API avec OAuth2

    Args:
        user (User): Utilisateur Django
        to_email (str): Destinataire
        subject (str): Sujet
        message_text (str): Corps du message

    Returns:
        dict: Résultat de l'envoi
    """
    import base64

    service = get_gmail_service(user)

    message = MIMEText(message_text)
    message['to'] = to_email
    message['subject'] = subject
    message['from'] = user.email

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')


    try:
        sent_message = service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()

        print(f"Email envoyé via Gmail API : {sent_message['id']}")

        return {
            'success': True,
            'message_id': sent_message['id']
        }
    except Exception as e:
        print(f"Erreur envoi Gmail API : {e}")
        return {
            'success': False,
            'error': str(e)
        }


def list_messages(user, max_results=10):
    """
    Liste les messages de la boîte mail de l'utilisateur

    Args:
        user (User): Utilisateur Django
        max_results (int): Nombre max de messages

    Returns:
        list: Liste des messages
    """
    service = get_gmail_service(user)

    results = service.users().messages().list(
        userId='me',
        maxResults=max_results
    ).execute()

    messages = results.get('messages', [])

    return messages