from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import RequestFactory, override_settings
from django.utils import timezone

from config.upload_validation import validate_uploaded_file
from config.views import protected_media
from management.models import OAuthToken


@pytest.mark.django_db
def test_oauth_tokens_are_encrypted_at_rest(authenticated_user):
    OAuthToken.objects.create(
        user=authenticated_user,
        provider="google",
        email="user@example.com",
        access_token="access-secret",
        refresh_token="refresh-secret",
        token_expiry=timezone.now() + timedelta(hours=1),
    )

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT access_token, refresh_token FROM oauth_tokens WHERE user_id = %s",
            [authenticated_user.pk],
        )
        stored_access, stored_refresh = cursor.fetchone()

    assert stored_access.startswith("fernet:v1:")
    assert stored_refresh.startswith("fernet:v1:")
    assert "access-secret" not in stored_access

    token = OAuthToken.objects.get(pk=authenticated_user.pk)
    assert token.access_token == "access-secret"
    assert token.refresh_token == "refresh-secret"


def test_upload_validation_checks_binary_signature():
    valid_pdf = SimpleUploadedFile(
        "document.pdf",
        b"%PDF-1.7\ncontent",
        content_type="application/pdf",
    )
    validate_uploaded_file(valid_pdf, {".pdf"})

    fake_pdf = SimpleUploadedFile(
        "document.pdf",
        b"not-a-pdf",
        content_type="application/pdf",
    )
    with pytest.raises(Exception, match="signature"):
        validate_uploaded_file(fake_pdf, {".pdf"})


@pytest.mark.django_db
def test_health_endpoints(client):
    assert client.get("/health/live/").json() == {"status": "ok"}
    response = client.get("/health/ready/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_protected_media_requires_an_authenticated_user(tmp_path, authenticated_user):
    media_file = tmp_path / "documents" / "private.txt"
    media_file.parent.mkdir()
    media_file.write_bytes(b"private-content")

    request = RequestFactory().get("/media/documents/private.txt")
    request.user = authenticated_user
    with override_settings(MEDIA_ROOT=tmp_path):
        response = protected_media(request, "documents/private.txt")

    assert response.status_code == 200
    assert b"".join(response.streaming_content) == b"private-content"
