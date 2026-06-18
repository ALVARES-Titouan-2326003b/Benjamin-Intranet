from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone

from technique.models import (
    TechnicalEmail,
    TechnicalEmailAttachment,
    TechnicalProject,
)
from technique.services.attachment_processing import process_attachment


@pytest.fixture
def attachment_setup(db, user_factory, tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    user = user_factory(username="tech-attachments", email="tech@example.com")
    project = TechnicalProject.objects.create(
        reference="TECH-PJ",
        name="Projet pièces jointes",
    )
    email = TechnicalEmail.objects.create(
        subject="Document technique",
        sender="sender@example.com",
        received_at=timezone.now(),
        imported_by=user,
        project=project,
        status="classified",
    )

    def create_attachment(name="contrat.txt", content=b"Texte du contrat"):
        return TechnicalEmailAttachment.objects.create(
            email=email,
            original_name=name,
            content_type="text/plain",
            size=len(content),
            file=SimpleUploadedFile(name, content),
        )

    return {
        "user": user,
        "project": project,
        "email": email,
        "create_attachment": create_attachment,
        "media_root": tmp_path,
    }


def summary():
    return {
        "resume": "Résumé",
        "prix": "1000 euros",
        "dates": "15 juin 2026",
        "conditions_suspensives": "",
        "penalites": "",
        "delais": "30 jours",
        "clauses_importantes": ["Clause importante"],
    }


@pytest.mark.django_db
def test_supported_attachment_creates_document_once(attachment_setup):
    attachment = attachment_setup["create_attachment"]()
    with (
        override_settings(MEDIA_ROOT=attachment_setup["media_root"]),
        patch(
            "technique.services.attachment_processing.extract_text_from_file",
            return_value="Texte extrait",
        ),
        patch(
            "technique.services.attachment_processing.summarize_document",
            return_value=summary(),
        ),
    ):
        first = process_attachment(attachment.pk)
        second = process_attachment(attachment.pk)

    attachment.refresh_from_db()
    assert first["created"] is True
    assert second["status"] == "linked"
    assert attachment.processing_status == "linked"
    assert attachment.linked_document.texte_brut == "Texte extrait"
    assert attachment.linked_document.created_by == attachment_setup["user"]
    assert attachment.linked_document.source_attachments.count() == 1


@pytest.mark.django_db
def test_unsupported_attachment_is_explicitly_skipped(attachment_setup):
    attachment = attachment_setup["create_attachment"]("photo.png", b"image")
    result = process_attachment(attachment.pk)

    attachment.refresh_from_db()
    assert result["status"] == "skipped"
    assert attachment.processing_status == "skipped"
    assert "non pris en charge" in attachment.processing_error
    assert attachment.linked_document is None


@pytest.mark.django_db
def test_extraction_error_is_visible(attachment_setup):
    attachment = attachment_setup["create_attachment"]()
    with patch(
        "technique.services.attachment_processing.extract_text_from_file",
        return_value="",
    ):
        result = process_attachment(attachment.pk)

    attachment.refresh_from_db()
    assert result["status"] == "error"
    assert attachment.processing_status == "error"
    assert "Aucun texte exploitable" in attachment.processing_error


@pytest.mark.django_db
def test_project_change_updates_linked_document_without_recreating(attachment_setup):
    attachment = attachment_setup["create_attachment"]()
    with (
        override_settings(MEDIA_ROOT=attachment_setup["media_root"]),
        patch(
            "technique.services.attachment_processing.extract_text_from_file",
            return_value="Texte extrait",
        ),
        patch(
            "technique.services.attachment_processing.summarize_document",
            return_value=summary(),
        ),
    ):
        process_attachment(attachment.pk)

    attachment.refresh_from_db()
    document_id = attachment.linked_document_id
    new_project = TechnicalProject.objects.create(
        reference="TECH-NEW",
        name="Nouveau projet",
    )
    attachment.email.project = new_project
    attachment.email.save(update_fields=["project"])
    result = process_attachment(attachment.pk)

    attachment.refresh_from_db()
    assert result["updated"] is True
    assert attachment.linked_document_id == document_id
    assert attachment.linked_document.projet == "TECH-NEW - Nouveau projet"
