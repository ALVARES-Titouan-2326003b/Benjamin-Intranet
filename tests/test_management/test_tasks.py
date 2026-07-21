import json
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone

from management.gmail_service import send_conversation_reminder, sync_conversation_journal
from invoices.models import ActeurExterne, Contact
from management.models import (
    EmailClient,
    GmailConversation,
    GmailConversationEvent,
    Metier,
    ModeleRelance,
    OAuthToken,
    TempsRelance,
)
from management.tasks import check_and_send_auto_relances


@pytest.fixture
def admin_gmail_user(user_factory):
    group = Group.objects.get_or_create(name="POLE_ADMINISTRATIF")[0]
    user = user_factory(username="admin-gmail", email="admin@example.com")
    user.groups.add(group)
    OAuthToken.objects.create(
        user=user,
        provider="google",
        email=user.email,
        access_token="access",
        refresh_token="refresh",
        token_expiry=timezone.now() + timedelta(hours=1),
    )
    return user


@pytest.mark.django_db
def test_sync_creates_journal_and_reply_has_priority(admin_gmail_user):
    sent = {
        "id": "sent-1",
        "threadId": "thread-1",
        "internalDate": "1781521200000",
        "snippet": "Premier message",
        "payload": {
            "headers": [
                {"name": "From", "value": "admin@example.com"},
                {"name": "To", "value": "client@example.com"},
                {"name": "Subject", "value": "Pièces manquantes"},
            ]
        },
    }
    reply = {
        "id": "reply-1",
        "threadId": "thread-1",
        "internalDate": "1781524800000",
        "payload": {
            "headers": [
                {"name": "From", "value": "client@example.com"},
                {"name": "To", "value": "admin@example.com"},
            ]
        },
    }

    with (
        patch("management.gmail_service.list_messages", return_value=[sent]),
        patch(
            "management.gmail_service.get_thread",
            return_value={"messages": [sent, reply]},
        ),
    ):
        stats = sync_conversation_journal(admin_gmail_user)

    conversation = GmailConversation.objects.get(thread_id="thread-1")
    assert stats == {"synced": 1, "replied": 1}
    assert conversation.status == "replied"
    assert conversation.recipient == "client@example.com"
    assert conversation.events.filter(event_type="reply_detected").exists()


@pytest.mark.django_db
def test_journal_status_and_notes_endpoints(client, admin_gmail_user):
    conversation = GmailConversation.objects.create(
        owner=admin_gmail_user,
        thread_id="thread-2",
        subject="Conversation",
        recipient="client@example.com",
        status="open",
    )
    client.force_login(admin_gmail_user)

    status_response = client.post(
        reverse("gmail_journal_status", args=[conversation.pk]),
        data=json.dumps({"status": "reminded"}),
        content_type="application/json",
    )
    note_response = client.post(
        reverse("gmail_journal_note", args=[conversation.pk]),
        data=json.dumps({"note": "Appel effectué le matin."}),
        content_type="application/json",
    )

    assert status_response.status_code == 200
    assert note_response.status_code == 200
    assert GmailConversationEvent.objects.filter(
        conversation=conversation,
        event_type="status_changed",
    ).exists()
    assert GmailConversationEvent.objects.filter(
        conversation=conversation,
        event_type="note",
        note="Appel effectué le matin.",
    ).exists()

    conversation.status = "replied"
    conversation.save(update_fields=["status"])
    blocked = client.post(
        reverse("gmail_journal_status", args=[conversation.pk]),
        data=json.dumps({"status": "open"}),
        content_type="application/json",
    )
    assert blocked.status_code == 409


@pytest.mark.django_db
def test_manual_reminder_keeps_complete_email_history(client, admin_gmail_user):
    conversation = GmailConversation.objects.create(
        owner=admin_gmail_user,
        thread_id="thread-history",
        initial_message_id="initial-history",
        last_message_id="last-history",
        subject="Documents compromis",
        recipient="notaire@example.com",
        status="open",
        sent_at=timezone.now() - timedelta(days=3),
    )

    with patch(
        "management.gmail_service.reply_to_message",
        return_value={
            "success": True,
            "message": "E-mail envoyé.",
            "message_id": "reminder-history-1",
            "thread_id": "thread-history",
        },
    ):
        send_conversation_reminder(
            conversation=conversation,
            user=admin_gmail_user,
            body="Merci de transmettre les pièces manquantes.",
            source="manual",
        )

    event = GmailConversationEvent.objects.get(
        conversation=conversation,
        event_type="reminder_sent",
    )
    assert event.reminder_source == "manual"
    assert event.reminder_subject == "Documents compromis"
    assert event.reminder_recipient == "notaire@example.com"
    assert event.note == "Merci de transmettre les pièces manquantes."
    assert event.external_message_id == "reminder-history-1"

    client.force_login(admin_gmail_user)
    response = client.get(reverse("admin_view"))
    content = response.content.decode()
    assert response.status_code == 200
    assert "Historique des relances e-mail" in content
    assert "Merci de transmettre les pièces manquantes." in content
    assert "notaire@example.com" in content


@pytest.mark.django_db
def test_celery_journal_sends_only_open_conversations(admin_gmail_user):
    open_conversation = GmailConversation.objects.create(
        owner=admin_gmail_user,
        thread_id="thread-open",
        subject="Ouverte",
        recipient="client@example.com",
        status="open",
        sent_at=timezone.now() - timedelta(days=10),
    )
    GmailConversation.objects.create(
        owner=admin_gmail_user,
        thread_id="thread-replied",
        subject="Répondue",
        recipient="other@example.com",
        status="replied",
        sent_at=timezone.now() - timedelta(days=10),
    )
    actor = ActeurExterne.objects.create(id="ADMIN-CLIENT")
    contact = Contact.objects.create(id="ADMIN-CONTACT", acteur=actor)
    metier = Metier.objects.create(nom="client")
    EmailClient.objects.create(
        contact=contact,
        metier=metier,
        email="client@example.com",
    )
    TempsRelance.objects.create(id=admin_gmail_user, temps=5)
    ModeleRelance.objects.create(
        utilisateur=admin_gmail_user,
        metier=metier,
        message="Relance administrative",
    )

    with (
        patch("management.tasks.sync_conversation_journal"),
        patch(
            "management.tasks.send_conversation_reminder",
            return_value={"success": True},
        ) as send,
    ):
        result = check_and_send_auto_relances()

    assert result["success"] is True
    assert send.call_count == 1
    assert send.call_args.kwargs["conversation"] == open_conversation
    assert send.call_args.kwargs["source"] == "automatic"
