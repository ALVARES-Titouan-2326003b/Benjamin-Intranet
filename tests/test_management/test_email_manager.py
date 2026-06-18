import base64
from datetime import timedelta
from email import message_from_bytes
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from management.gmail_service import reply_to_message, send_message
from management.models import OAuthToken
from management.oauth_utils import GOOGLE_SCOPES, get_authorization_url, get_valid_credentials


@pytest.fixture
def google_user(user_factory):
    user = user_factory(username="gmail-user", email="gmail@example.com")
    OAuthToken.objects.create(
        user=user,
        provider="google",
        email=user.email,
        access_token="access",
        refresh_token="refresh",
        token_expiry=timezone.now() + timedelta(hours=1),
    )
    return user


def test_google_oauth_requests_send_scope_and_new_consent():
    url, state = get_authorization_url("https://example.test/oauth/callback/", provider="google")
    assert state
    assert "gmail.send" in url
    assert "prompt=consent" in url
    assert "https://www.googleapis.com/auth/gmail.send" in GOOGLE_SCOPES


@pytest.mark.django_db
def test_send_message_builds_mime_and_thread_payload(google_user):
    service = MagicMock()
    service.users().messages().send().execute.return_value = {
        "id": "sent-id",
        "threadId": "thread-1",
    }

    with patch("management.gmail_service.get_gmail_service", return_value=service):
        result = send_message(
            google_user,
            "client@example.com",
            "Re: Dossier",
            "Corps du message",
            thread_id="thread-1",
            in_reply_to="<original@example.com>",
            references="<older@example.com> <original@example.com>",
        )

    payload = service.users().messages().send.call_args.kwargs["body"]
    mime = message_from_bytes(base64.urlsafe_b64decode(payload["raw"]))
    assert payload["threadId"] == "thread-1"
    assert mime["From"] == "gmail@example.com"
    assert mime["To"] == "client@example.com"
    assert mime["Message-ID"]
    assert mime["In-Reply-To"] == "<original@example.com>"
    assert "<original@example.com>" in mime["References"]
    assert result["message_id"] == "sent-id"


@pytest.mark.django_db
def test_reply_uses_original_gmail_headers(google_user):
    original = {
        "id": "message-1",
        "threadId": "thread-1",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Dossier"},
                {"name": "To", "value": "client@example.com"},
                {"name": "Message-ID", "value": "<message-1@example.com>"},
                {"name": "References", "value": "<root@example.com>"},
            ]
        },
    }
    with (
        patch("management.gmail_service.get_message", return_value=original),
        patch("management.gmail_service.send_message") as send,
    ):
        reply_to_message(google_user, "message-1", "Relance")

    kwargs = send.call_args.kwargs
    args = send.call_args.args
    assert kwargs["thread_id"] == "thread-1"
    assert args[2] == "Re: Dossier"
    assert kwargs["in_reply_to"] == "<message-1@example.com>"
    assert "<message-1@example.com>" in kwargs["references"]


@pytest.mark.django_db
def test_expired_google_token_is_refreshed(google_user):
    token = google_user.oauth_token
    token.token_expiry = timezone.now() - timedelta(minutes=1)
    token.save(update_fields=["token_expiry"])

    with patch(
        "management.oauth_utils.refresh_access_token",
        return_value={
            "access_token": "new-access",
            "refresh_token": "new-refresh",
            "token_expiry": timezone.now() + timedelta(hours=1),
        },
    ) as refresh:
        assert get_valid_credentials(token) == "new-access"

    refresh.assert_called_once_with("refresh", "google")
    token.refresh_from_db()
    assert token.refresh_token == "new-refresh"
