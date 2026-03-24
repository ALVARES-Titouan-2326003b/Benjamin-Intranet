"""
Utilitaires OAuth2 pour l'authentification Microsoft/Outlook
"""
import os
from datetime import timedelta
from urllib.parse import urlencode

import requests
from django.utils import timezone

MICROSOFT_CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID")
MICROSOFT_CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET")
TENANT_ID = os.getenv("MICROSOFT_TENANT_ID", "common")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
GRAPH_URL = "https://graph.microsoft.com/v1.0"

SCOPES = [
    "openid",
    "offline_access",
    "User.Read",
    "Mail.Read",
    "Mail.Send",
    "Mail.ReadWrite",
]


def get_authorization_url(redirect_uri):
    import secrets

    state = secrets.token_urlsafe(32)

    params = {
        "client_id": MICROSOFT_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "response_mode": "query",
        "scope": " ".join(SCOPES),
        "state": state,
    }

    authorization_url = f"{AUTHORITY}/oauth2/v2.0/authorize?{urlencode(params)}"
    return authorization_url, state


def exchange_code_for_tokens(code, redirect_uri):
    token_url = f"{AUTHORITY}/oauth2/v2.0/token"

    data = {
        "client_id": MICROSOFT_CLIENT_ID,
        "client_secret": MICROSOFT_CLIENT_SECRET,
        "code": code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
        "scope": " ".join(SCOPES),
    }

    response = requests.post(token_url, data=data, timeout=20)
    response.raise_for_status()
    tokens = response.json()

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    me_response = requests.get(f"{GRAPH_URL}/me", headers=headers, timeout=20)
    me_response.raise_for_status()
    user_info = me_response.json()
    print(user_info)

    token_expiry = timezone.now() + timedelta(seconds=tokens.get("expires_in", 3600))

    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token", ""),
        "token_expiry": token_expiry,
        "email": user_info.get("mail") or user_info.get("userPrincipalName"),
    }


def refresh_access_token(refresh_token):
    token_url = f"{AUTHORITY}/oauth2/v2.0/token"

    data = {
        "client_id": MICROSOFT_CLIENT_ID,
        "client_secret": MICROSOFT_CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
        "scope": " ".join(SCOPES),
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
        new_tokens = refresh_access_token(oauth_token.refresh_token)
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