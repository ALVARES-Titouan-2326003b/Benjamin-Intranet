import base64
from datetime import datetime, timezone as dt_timezone
from email.message import EmailMessage
from email.utils import make_msgid, parseaddr, parsedate_to_datetime

from django.utils import timezone

from management.models import (
    GmailConversation,
    GmailConversationEvent,
    OAuthToken,
)
from management.oauth_utils import get_gmail_service


def _headers(payload):
    return {
        item.get("name", "").lower(): item.get("value", "")
        for item in payload.get("headers", [])
    }


def _parse_gmail_date(message, headers):
    raw = headers.get("date")
    if raw:
        try:
            value = parsedate_to_datetime(raw)
            if value.tzinfo is None:
                value = value.replace(tzinfo=dt_timezone.utc)
            return value
        except (TypeError, ValueError):
            pass
    internal_date = message.get("internalDate")
    if internal_date:
        return datetime.fromtimestamp(int(internal_date) / 1000, tz=dt_timezone.utc)
    return timezone.now()


def _first_address(value):
    return parseaddr(value or "")[1]


def _get_google_token(user):
    token = OAuthToken.objects.filter(user=user, provider="google").first()
    if not token:
        raise ValueError("Aucun compte Gmail synchronisé pour cet utilisateur.")
    return token


def list_messages(user, label_ids=None, query=None, limit=50):
    _get_google_token(user)
    service = get_gmail_service(user)
    kwargs = {"userId": "me", "maxResults": min(limit, 100)}
    if label_ids:
        kwargs["labelIds"] = label_ids
    if query:
        kwargs["q"] = query

    response = service.users().messages().list(**kwargs).execute()
    messages = []
    for ref in response.get("messages", [])[:limit]:
        messages.append(
            service.users().messages().get(
                userId="me",
                id=ref["id"],
                format="metadata",
                metadataHeaders=[
                    "Subject",
                    "From",
                    "To",
                    "Date",
                    "Message-ID",
                    "In-Reply-To",
                    "References",
                ],
            ).execute()
        )
    return messages


def get_message(user, message_id, format="metadata"):
    _get_google_token(user)
    kwargs = {"userId": "me", "id": message_id, "format": format}
    if format == "metadata":
        kwargs["metadataHeaders"] = [
            "Subject",
            "From",
            "To",
            "Date",
            "Message-ID",
            "In-Reply-To",
            "References",
        ]
    return get_gmail_service(user).users().messages().get(**kwargs).execute()


def get_thread(user, thread_id):
    _get_google_token(user)
    return (
        get_gmail_service(user)
        .users()
        .threads()
        .get(userId="me", id=thread_id, format="metadata")
        .execute()
    )


def _build_raw_message(sender, to_email, subject, body, in_reply_to="", references=""):
    message = EmailMessage()
    message["From"] = sender
    message["To"] = to_email
    message["Subject"] = subject
    sender_domain = sender.rsplit("@", 1)[-1] if "@" in sender else None
    message["Message-ID"] = make_msgid(domain=sender_domain)
    if in_reply_to:
        message["In-Reply-To"] = in_reply_to
    if references:
        message["References"] = references
    message.set_content(body)
    return base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")


def send_message(user, to_email, subject, body, thread_id=None, in_reply_to="", references=""):
    token = _get_google_token(user)
    payload = {
        "raw": _build_raw_message(
            token.email,
            to_email,
            subject,
            body,
            in_reply_to=in_reply_to,
            references=references,
        )
    }
    if thread_id:
        payload["threadId"] = thread_id
    sent = (
        get_gmail_service(user)
        .users()
        .messages()
        .send(userId="me", body=payload)
        .execute()
    )
    return {
        "success": True,
        "message": "E-mail envoyé avec succès via Gmail.",
        "message_id": sent.get("id", ""),
        "thread_id": sent.get("threadId", thread_id or ""),
    }


def reply_to_message(user, message_id, body, subject="", to_email=""):
    original = get_message(user, message_id)
    headers = _headers(original.get("payload", {}))
    thread_id = original.get("threadId", "")
    recipient = to_email or _first_address(headers.get("to")) or _first_address(headers.get("from"))
    original_subject = subject or headers.get("subject") or "(Sans objet)"
    reply_subject = original_subject if original_subject.lower().startswith("re:") else f"Re: {original_subject}"
    message_id_header = headers.get("message-id", "")
    references = headers.get("references", "")
    if message_id_header and message_id_header not in references:
        references = f"{references} {message_id_header}".strip()
    return send_message(
        user,
        recipient,
        reply_subject,
        body,
        thread_id=thread_id,
        in_reply_to=message_id_header,
        references=references,
    )


def _thread_has_external_reply(messages, own_email):
    own_email = (own_email or "").lower()
    sent_dates = []
    external_dates = []
    for message in messages:
        headers = _headers(message.get("payload", {}))
        sender = _first_address(headers.get("from")).lower()
        date = _parse_gmail_date(message, headers)
        if sender == own_email:
            sent_dates.append(date)
        else:
            external_dates.append(date)
    if not sent_dates or not external_dates:
        return False, None
    first_sent = min(sent_dates)
    replies = [date for date in external_dates if date >= first_sent]
    return bool(replies), max(replies) if replies else None


def sync_conversation_journal(user, limit=100):
    token = _get_google_token(user)
    sent_messages = list_messages(user, label_ids=["SENT"], limit=limit)
    synced = 0
    replied = 0

    for message in sent_messages:
        headers = _headers(message.get("payload", {}))
        thread_id = message.get("threadId") or message.get("id")
        if not thread_id:
            continue

        sent_at = _parse_gmail_date(message, headers)
        conversation, created = GmailConversation.objects.get_or_create(
            owner=user,
            thread_id=thread_id,
            defaults={
                "initial_message_id": message.get("id", ""),
                "last_message_id": message.get("id", ""),
                "subject": headers.get("subject", "(Sans objet)"),
                "recipient": _first_address(headers.get("to")),
                "preview": message.get("snippet", ""),
                "sent_at": sent_at,
                "last_synced_at": timezone.now(),
            },
        )

        thread = get_thread(user, thread_id)
        thread_messages = thread.get("messages", [])
        has_reply, replied_at = _thread_has_external_reply(thread_messages, token.email)
        old_status = conversation.status
        conversation.last_message_id = (
            thread_messages[-1].get("id", message.get("id", ""))
            if thread_messages
            else message.get("id", "")
        )
        conversation.subject = headers.get("subject", conversation.subject)
        conversation.recipient = _first_address(headers.get("to")) or conversation.recipient
        conversation.preview = message.get("snippet", conversation.preview)
        conversation.sent_at = min(filter(None, [conversation.sent_at, sent_at]))
        conversation.last_synced_at = timezone.now()
        if has_reply:
            conversation.status = "replied"
            conversation.replied_at = replied_at
        conversation.save()

        if created:
            GmailConversationEvent.objects.create(
                conversation=conversation,
                event_type="synced",
                external_message_id=message.get("id", ""),
            )
        if has_reply and old_status != "replied":
            GmailConversationEvent.objects.create(
                conversation=conversation,
                event_type="reply_detected",
                old_status=old_status,
                new_status="replied",
                external_message_id=conversation.last_message_id,
            )
            replied += 1
        synced += 1

    return {"synced": synced, "replied": replied}


def send_conversation_reminder(conversation, user, body, source="manual"):
    if conversation.status == "replied":
        raise ValueError(
            "Cette conversation contient déjà une réponse Gmail et ne peut plus être relancée."
        )
    if source not in {"manual", "automatic"}:
        raise ValueError("Origine de relance invalide.")
    result = reply_to_message(
        user=user,
        message_id=conversation.last_message_id or conversation.initial_message_id,
        body=body,
        subject=conversation.subject,
        to_email=conversation.recipient,
    )
    old_status = conversation.status
    conversation.status = "reminded"
    conversation.last_reminded_at = timezone.now()
    conversation.last_message_id = result.get("message_id", conversation.last_message_id)
    conversation.save(
        update_fields=[
            "status",
            "last_reminded_at",
            "last_message_id",
            "updated_at",
        ]
    )
    GmailConversationEvent.objects.create(
        conversation=conversation,
        event_type="reminder_sent",
        user=user,
        old_status=old_status,
        new_status="reminded",
        note=body,
        reminder_source=source,
        reminder_subject=conversation.subject,
        reminder_recipient=conversation.recipient,
        external_message_id=result.get("message_id", ""),
    )
    return result
