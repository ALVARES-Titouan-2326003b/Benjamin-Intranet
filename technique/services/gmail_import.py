import base64
import traceback
from email.utils import parsedate_to_datetime

from django.utils import timezone
from django.core.files.base import ContentFile

from management.models import OAuthToken
from management.oauth_utils import get_gmail_service
from technique.models import TechnicalEmail, TechnicalEmailAttachment


def import_technique_emails(user, max_results: int = 50) -> dict:
    """
    Importe les emails de la boîte Gmail de l'utilisateur dans TechnicalEmail.

    Chaque utilisateur a sa propre boîte — les emails sont strictement personnels.
    Dédoublonnage par (external_id, imported_by) : un même ID Gmail peut exister
    pour deux utilisateurs différents sans conflit.
    """
    try:
        OAuthToken.objects.get(user=user)
    except OAuthToken.DoesNotExist:
        raise ValueError(
            f"L'utilisateur {user.username} n'a pas synchronisé sa boîte mail. "
            "Cliquez sur « Synchroniser boîte mail » pour autoriser l'accès."
        )

    stats = {"imported": 0, "skipped": 0, "errors": 0}

    try:
        service = get_gmail_service(user)

        results = service.users().messages().list(
            userId="me",
            maxResults=max_results,
            labelIds=["INBOX"],
        ).execute()

        message_refs = results.get("messages", [])
        print(f"[gmail_import] {len(message_refs)} message(s) trouvé(s) dans INBOX pour {user.username}")

        for ref in message_refs:
            gmail_id = ref["id"]

            if TechnicalEmail.objects.filter(
                external_id=gmail_id,
                imported_by=user,
            ).exists():
                stats["skipped"] += 1
                continue

            try:
                msg_data = service.users().messages().get(
                    userId="me",
                    id=gmail_id,
                    format="full",
                ).execute()

                email_obj = _create_technical_email(msg_data, user)

                if email_obj:
                    _process_attachments(service, gmail_id, msg_data, email_obj)
                    stats["imported"] += 1
                else:
                    stats["skipped"] += 1

            except Exception as exc:
                print(f"[gmail_import] Erreur sur le message {gmail_id} : {exc}")
                traceback.print_exc()
                stats["errors"] += 1

    except Exception as exc:
        print(f"[gmail_import] Erreur globale : {exc}")
        traceback.print_exc()
        raise

    print(
        f"[gmail_import] {user.username} — "
        f"{stats['imported']} importé(s), "
        f"{stats['skipped']} ignoré(s), "
        f"{stats['errors']} erreur(s)"
    )
    return stats


def _create_technical_email(msg_data: dict, user) -> TechnicalEmail | None:
    gmail_id = msg_data["id"]
    headers = {
        h["name"]: h["value"]
        for h in msg_data.get("payload", {}).get("headers", [])
    }

    subject    = headers.get("Subject", "(Sans objet)")
    sender     = headers.get("From", "")
    recipients = headers.get("To", "")
    cc         = headers.get("Cc", "")
    date_str   = headers.get("Date", "")

    try:
        received_at = parsedate_to_datetime(date_str)
    except (TypeError, ValueError):
        received_at = timezone.now()

    body             = _extract_body(msg_data.get("payload", {}))
    has_attachments  = _has_attachments(msg_data.get("payload", {}))

    return TechnicalEmail.objects.create(
        external_id=gmail_id,
        subject=subject,
        sender=sender,
        recipients=recipients,
        cc=cc,
        body=body,
        received_at=received_at,
        has_attachments=has_attachments,
        status="unassigned",
        imported_by=user,
    )


def _extract_body(payload: dict) -> str:
    mime_type = payload.get("mimeType", "")

    if "parts" not in payload:
        data = payload.get("body", {}).get("data", "")
        if not data:
            return ""
        decoded = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
        if mime_type == "text/html":
            return _strip_html(decoded)
        return decoded

    plain_body = ""
    html_body  = ""

    for part in payload.get("parts", []):
        part_type = part.get("mimeType", "")
        if part_type == "text/plain":
            plain_body = _extract_body(part)
        elif part_type == "text/html" and not plain_body:
            html_body = _extract_body(part)
        elif part_type.startswith("multipart/"):
            nested = _extract_body(part)
            if nested:
                plain_body = plain_body or nested

    return plain_body or html_body


def _strip_html(html: str) -> str:
    import re
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()


def _has_attachments(payload: dict) -> bool:
    for part in payload.get("parts", []):
        if part.get("filename") and part.get("body", {}).get("attachmentId"):
            return True
        if part.get("parts") and _has_attachments(part):
            return True
    return False


def _process_attachments(service, gmail_id: str, msg_data: dict, email_obj: TechnicalEmail):
    payload = msg_data.get("payload", {})
    _process_parts(service, gmail_id, payload.get("parts", []), email_obj)


def _process_parts(service, gmail_id: str, parts: list, email_obj: TechnicalEmail):
    for part in parts:
        filename      = part.get("filename", "")
        attachment_id = part.get("body", {}).get("attachmentId")
        content_type  = part.get("mimeType", "")
        size          = part.get("body", {}).get("size", 0)

        if filename and attachment_id:
            try:
                attachment_data = service.users().messages().attachments().get(
                    userId="me", messageId=gmail_id, id=attachment_id,
                ).execute()

                file_data = base64.urlsafe_b64decode(
                    attachment_data.get("data", "") + "=="
                )

                attachment = TechnicalEmailAttachment(
                    email=email_obj,
                    original_name=filename,
                    content_type=content_type,
                    size=size,
                )
                attachment.file.save(filename, ContentFile(file_data), save=True)
                print(f"[gmail_import] PJ sauvegardée : {filename}")

            except Exception as exc:
                print(f"[gmail_import] Erreur PJ {filename} : {exc}")

        if part.get("parts"):
            _process_parts(service, gmail_id, part["parts"], email_obj)