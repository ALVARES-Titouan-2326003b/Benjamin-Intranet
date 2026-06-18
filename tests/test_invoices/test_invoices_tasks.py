from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from invoices.models import (
    ActeurExterne,
    Client,
    Contact,
    EmailFournisseur,
    Facture,
    FactureHistorique,
    Fournisseur,
    InvoiceReminderSettings,
    RelanceFournisseur,
)
from invoices.tasks import check_and_send_invoice_reminders
from management.models import OAuthToken
from technique.models import TechnicalProject


User = get_user_model()


@pytest.fixture
def invoice_setup(db):
    sender = User.objects.create_user(
        username="finance-gmail",
        email="finance@example.com",
        password="test",
    )
    OAuthToken.objects.create(
        user=sender,
        provider="google",
        email=sender.email,
        access_token="access",
        refresh_token="refresh",
        token_expiry=timezone.now() + timedelta(hours=1),
    )
    InvoiceReminderSettings.objects.create(sender=sender)
    RelanceFournisseur.objects.create(
        id="finance",
        temps=3,
        message="Facture {facture_id}, retard {jours_retard} jours.",
    )

    supplier_actor = ActeurExterne.objects.create(id="SUPPLIER")
    supplier = Fournisseur.objects.create(id=supplier_actor, nom="Fournisseur")
    contact = Contact.objects.create(id="CONTACT", acteur=supplier_actor)
    EmailFournisseur.objects.create(contact=contact, email="supplier@example.com")

    client_actor = ActeurExterne.objects.create(id="CLIENT")
    invoice_client = Client.objects.create(id=client_actor)
    project = TechnicalProject.objects.create(
        reference="TECH-REMINDER",
        name="Projet relances",
    )

    def create_invoice(invoice_id, days_overdue, status="received"):
        due = timezone.now() - timedelta(days=days_overdue)
        return Facture.objects.create(
            id=invoice_id,
            dossier=project,
            fournisseur=supplier,
            client=invoice_client,
            montant=1200,
            statut=status,
            echeance=due,
        )

    return {
        "sender": sender,
        "create_invoice": create_invoice,
    }


@pytest.mark.django_db
def test_first_reminder_is_sent_at_j_plus_x(invoice_setup):
    invoice = invoice_setup["create_invoice"]("FAC-J3", 3)

    with patch(
        "invoices.tasks.send_message",
        return_value={"success": True, "message_id": "gmail-1"},
    ) as send:
        result = check_and_send_invoice_reminders()

    assert result["relances_envoyees"] == 1
    send.assert_called_once()
    history = FactureHistorique.objects.get(facture=invoice, action="reminder_sent")
    assert history.days_overdue == 3
    assert history.recipient_email == "supplier@example.com"
    assert history.external_message_id == "gmail-1"


@pytest.mark.django_db
def test_reminder_catches_up_after_interruption(invoice_setup):
    invoice = invoice_setup["create_invoice"]("FAC-CATCHUP", 5)

    with patch(
        "invoices.tasks.send_message",
        return_value={"success": True, "message_id": "gmail-catchup"},
    ):
        result = check_and_send_invoice_reminders()

    assert result["relances_envoyees"] == 1
    assert FactureHistorique.objects.get(facture=invoice).days_overdue == 5


@pytest.mark.django_db
def test_next_reminder_uses_last_success_and_prevents_duplicates(invoice_setup):
    invoice = invoice_setup["create_invoice"]("FAC-REPEAT", 8)
    FactureHistorique.objects.create(
        facture=invoice,
        action="reminder_sent",
        days_overdue=5,
        recipient_email="supplier@example.com",
        external_message_id="gmail-old",
    )

    with patch(
        "invoices.tasks.send_message",
        return_value={"success": True, "message_id": "gmail-new"},
    ) as send:
        first = check_and_send_invoice_reminders()
        second = check_and_send_invoice_reminders()

    assert first["relances_envoyees"] == 1
    assert second["relances_envoyees"] == 0
    assert send.call_count == 1
    assert FactureHistorique.objects.filter(
        facture=invoice,
        action="reminder_sent",
    ).count() == 2


@pytest.mark.django_db
@pytest.mark.parametrize("status", ["paid", "denied", "archived"])
def test_stop_statuses_are_never_reminded(invoice_setup, status):
    invoice_setup["create_invoice"](f"FAC-{status}", 30, status=status)

    with patch("invoices.tasks.send_message") as send:
        result = check_and_send_invoice_reminders()

    assert result["factures_traitees"] == 0
    send.assert_not_called()


@pytest.mark.django_db
def test_missing_or_inactive_gmail_sender_is_reported(invoice_setup):
    InvoiceReminderSettings.objects.update(sender=None)
    result = check_and_send_invoice_reminders()
    assert result["success"] is False
    assert "Aucun compte Gmail actif" in result["message"]

    InvoiceReminderSettings.objects.update(sender=invoice_setup["sender"])
    invoice_setup["sender"].is_active = False
    invoice_setup["sender"].save(update_fields=["is_active"])
    result = check_and_send_invoice_reminders()
    assert result["success"] is False
    assert "Aucun compte Gmail actif" in result["message"]


@pytest.mark.django_db
def test_invalid_or_expired_sender_token_is_reported(invoice_setup):
    with patch(
        "invoices.tasks.get_valid_credentials",
        side_effect=RuntimeError("refresh failed"),
    ):
        result = check_and_send_invoice_reminders()

    assert result["success"] is False
    assert "jeton Gmail" in result["message"]
