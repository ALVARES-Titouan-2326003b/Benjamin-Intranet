"""
Utilitaires OAuth2 pour l'authentification Microsoft/Outlook et Google/Gmail
"""
import os
from datetime import timedelta
from urllib.parse import urlencode

import requests
from django.utils import timezone

MICROSOFT_CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID")
MICROSOFT_CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET")
TENANT_ID = os.getenv("MICROSOFT_TENANT_ID", "common")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
GRAPH_URL = "https://graph.microsoft.com/v1.0"

MICROSOFT_SCOPES = [
    "openid",
    "offline_access",
    "User.Read",
    "Mail.Read",
    "Mail.Send",
    "Mail.ReadWrite",
]

GOOGLE_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]


def get_authorization_url(redirect_uri, provider="microsoft"):
    import secrets

    state = secrets.token_urlsafe(32)

    if provider == "google":
        params = {
            "client_id": GOOGLE_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": " ".join(GOOGLE_SCOPES),
            "access_type": "offline",
            "state": state,
        }
        authorization_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    else:  # microsoft
        params = {
            "client_id": MICROSOFT_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "response_mode": "query",
            "scope": " ".join(MICROSOFT_SCOPES),
            "state": state,
        }
        authorization_url = f"{AUTHORITY}/oauth2/v2.0/authorize?{urlencode(params)}"

    return authorization_url, state


def exchange_code_for_tokens(code, redirect_uri, provider="microsoft"):
    if provider == "google":
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
    else:  # microsoft
        token_url = f"{AUTHORITY}/oauth2/v2.0/token"
        data = {
            "client_id": MICROSOFT_CLIENT_ID,
            "client_secret": MICROSOFT_CLIENT_SECRET,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
            "scope": " ".join(MICROSOFT_SCOPES),
        }

    response = requests.post(token_url, data=data, timeout=20)
    response.raise_for_status()
    tokens = response.json()

    # Get user info
    if provider == "google":
        # For Google, try to get email from tokeninfo endpoint
        tokeninfo_url = f"https://oauth2.googleapis.com/tokeninfo?access_token={tokens['access_token']}"
        me_response = requests.get(tokeninfo_url, timeout=20)
        if me_response.status_code == 200:
            user_info = me_response.json()
            email = user_info.get("email")
        else:
            # Fallback: try userinfo endpoint
            headers = {"Authorization": f"Bearer {tokens['access_token']}"}
            me_response = requests.get("https://www.googleapis.com/oauth2/v2/userinfo", headers=headers, timeout=20)
            me_response.raise_for_status()
            user_info = me_response.json()
            email = user_info.get("email")
    else:  # microsoft
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        me_response = requests.get(f"{GRAPH_URL}/me", headers=headers, timeout=20)
        me_response.raise_for_status()
        user_info = me_response.json()
        email = user_info.get("mail") or user_info.get("userPrincipalName")

    token_expiry = timezone.now() + timedelta(seconds=tokens.get("expires_in", 3600))

    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token", ""),
        "token_expiry": token_expiry,
        "email": email,
    }


def refresh_access_token(refresh_token, provider="microsoft"):
    if provider == "google":
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
    else:  # microsoft
        token_url = f"{AUTHORITY}/oauth2/v2.0/token"
        data = {
            "client_id": MICROSOFT_CLIENT_ID,
            "client_secret": MICROSOFT_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "scope": " ".join(MICROSOFT_SCOPES),
        }

    response = requests.post(token_url, data=data, timeout=20)
    response.raise_for_status()
    tokens = response.json()

    token_expiry = timezone.now() + timedelta(seconds=tokens.get("expires_in", 3600))

    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token", refresh_token),
        "token_expiry": token_expiry,
    }


def get_valid_credentials(oauth_token):
    if timezone.now() >= (oauth_token.token_expiry - timedelta(minutes=5)):
        new_tokens = refresh_access_token(oauth_token.refresh_token, oauth_token.provider)
        oauth_token.access_token = new_tokens["access_token"]
        oauth_token.refresh_token = new_tokens["refresh_token"]
        oauth_token.token_expiry = new_tokens["token_expiry"]
        oauth_token.save(update_fields=["access_token", "refresh_token", "token_expiry"])

    return oauth_token.access_token


def get_graph_headers(user):
    from management.models import OAuthToken

    oauth_token = OAuthToken.objects.get(user=user)
    access_token = get_valid_credentials(oauth_token)

    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }


def send_email_via_graph_api(user, to_email, subject, message_text):
    headers = get_graph_headers(user)

    payload = {
        "message": {
            "subject": subject,
            "body": {
                "contentType": "Text",
                "content": message_text,
            },
            "toRecipients": [
                {"emailAddress": {"address": to_email}}
            ],
        },
        "saveToSentItems": True,
    }

    response = requests.post(
        f"{GRAPH_URL}/me/sendMail",
        headers=headers,
        json=payload,
        timeout=20,
    )

    if response.status_code == 202:
        return {"success": True, "message_id": None}

    return {"success": False, "error": response.text}


def get_gmail_service(user):
    """
    Retourne un service Gmail API pour l'utilisateur
    """
    from googleapiclient.discovery import build
    from management.models import OAuthToken

    oauth_token = OAuthToken.objects.get(user=user)
    if oauth_token.provider != "google":
        raise ValueError("Token OAuth n'est pas pour Google/Gmail")

    access_token = get_valid_credentials(oauth_token)

    from google.oauth2.credentials import Credentials
    creds = Credentials(
        token=access_token,
        refresh_token=oauth_token.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=GOOGLE_SCOPES
    )

    service = build('gmail', 'v1', credentials=creds)
    return service