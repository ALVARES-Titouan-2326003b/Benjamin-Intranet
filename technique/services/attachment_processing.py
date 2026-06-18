import json
from pathlib import Path

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from technique.models import DocumentTechnique, TechnicalEmailAttachment
from technique.services.ai_summary import summarize_document
from technique.services.documents import extract_text_from_file


SUPPORTED_SUFFIXES = {".pdf", ".doc", ".docx", ".txt"}


def _project_label(project):
    return f"{project.reference} - {project.name}"


def _mark(attachment, status, error=""):
    attachment.processing_status = status
    attachment.processing_error = error
    attachment.processed_at = timezone.now()
    attachment.save(
        update_fields=[
            "processing_status",
            "processing_error",
            "processed_at",
        ]
    )


def process_attachment(attachment_id):
    attachment = (
        TechnicalEmailAttachment.objects.select_related(
            "email__project",
            "email__imported_by",
            "linked_document",
        )
        .get(pk=attachment_id)
    )
    project = attachment.email.project

    if not project:
        _mark(attachment, "pending", "")
        return {"status": "pending", "attachment_id": attachment.pk}

    if attachment.linked_document_id:
        document = attachment.linked_document
        project_label = _project_label(project)
        if document.projet != project_label:
            document.projet = project_label
            document.save(update_fields=["projet"])
        _mark(attachment, "linked", "")
        return {
            "status": "linked",
            "attachment_id": attachment.pk,
            "document_id": document.pk,
            "updated": True,
        }

    suffix = Path(attachment.original_name or attachment.file.name).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        _mark(
            attachment,
            "skipped",
            f"Format {suffix or 'sans extension'} non pris en charge.",
        )
        return {"status": "skipped", "attachment_id": attachment.pk}

    claimed = TechnicalEmailAttachment.objects.filter(
        pk=attachment.pk,
        linked_document__isnull=True,
        processing_status__in=["pending", "error"],
    ).update(
        processing_status="processing",
        processing_error="",
        processed_at=None,
    )
    if not claimed:
        attachment.refresh_from_db()
        return {
            "status": attachment.processing_status,
            "attachment_id": attachment.pk,
            "document_id": attachment.linked_document_id,
            "already_processing": attachment.processing_status == "processing",
        }

    attachment.refresh_from_db()
    try:
        attachment.file.open("rb")
        raw_content = attachment.file.read()
        attachment.file.seek(0)
        extracted_text = extract_text_from_file(attachment.file) or ""
        attachment.file.close()

        if not extracted_text.strip():
            raise ValueError("Aucun texte exploitable n'a pu être extrait du fichier.")

        summary = summarize_document(extracted_text[:500000])

        with transaction.atomic():
            locked = (
                TechnicalEmailAttachment.objects.select_for_update()
                .select_related("email__project", "email__imported_by", "linked_document")
                .get(pk=attachment.pk)
            )
            if locked.linked_document_id:
                return {
                    "status": "linked",
                    "attachment_id": locked.pk,
                    "document_id": locked.linked_document_id,
                }
            if not locked.email.project_id:
                _mark(locked, "pending", "")
                return {"status": "pending", "attachment_id": locked.pk}

            document = DocumentTechnique(
                projet=_project_label(locked.email.project),
                titre=Path(locked.original_name).stem[:255] or "Document Gmail",
                type_document="autre",
                texte_brut=extracted_text[:500000],
                resume=(summary.get("resume") or "")[:50000],
                prix=(summary.get("prix") or "")[:20000],
                dates=(summary.get("dates") or "")[:20000],
                conditions_suspensives=(
                    summary.get("conditions_suspensives") or ""
                )[:20000],
                penalites=(summary.get("penalites") or "")[:20000],
                delais=(summary.get("delais") or "")[:20000],
                clauses_importantes=json.dumps(
                    summary.get("clauses_importantes") or [],
                    ensure_ascii=False,
                )[:50000],
                created_by=locked.email.imported_by,
            )
            document.fichier.save(
                locked.original_name,
                ContentFile(raw_content),
                save=False,
            )
            document.save()

            locked.extracted_text = extracted_text[:500000]
            locked.linked_document = document
            locked.processing_status = "linked"
            locked.processing_error = ""
            locked.processed_at = timezone.now()
            locked.save(
                update_fields=[
                    "extracted_text",
                    "linked_document",
                    "processing_status",
                    "processing_error",
                    "processed_at",
                ]
            )

        return {
            "status": "linked",
            "attachment_id": attachment.pk,
            "document_id": document.pk,
            "created": True,
        }
    except Exception as exc:
        attachment.refresh_from_db()
        if not attachment.linked_document_id:
            _mark(attachment, "error", str(exc))
        return {
            "status": "error",
            "attachment_id": attachment.pk,
            "error": str(exc),
        }
