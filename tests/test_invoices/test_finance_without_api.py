from datetime import timedelta

import pytest
from django.contrib.auth.models import Group, User
from django.utils import timezone
from unittest.mock import patch

from invoices.models import (
    ActeurExterne,
    Client,
    Contact,
    EmailFournisseur,
    Entreprise,
    Facture,
    FactureHistorique,
    Fournisseur,
    InvoiceReminderSettings,
    RelanceFournisseur,
)
from management.models import OAuthToken
from invoices.services.cegid import build_cegid_line, generate_cegid_export
from invoices.services.quality import get_invoice_anomalies
from invoices.tasks import check_and_send_invoice_reminders
from invoices.views_dashboard import DashboardView
from technique.models import TechnicalProject


@pytest.fixture
def finance_user(db):
    group, _ = Group.objects.get_or_create(name="POLE_FINANCIER")
    user = User.objects.create_user(username="finance", email="finance@example.com")
    user.groups.add(group)
    return user


@pytest.fixture
def project(db):
    return TechnicalProject.objects.create(reference="TECH-001", name="Projet Test")


@pytest.fixture
def supplier(db):
    actor = ActeurExterne.objects.create(id="SUP-001")
    return Fournisseur.objects.create(id=actor, nom="Fournisseur Énergie")


@pytest.fixture
def client_entity(db):
    actor = ActeurExterne.objects.create(id="CLI-001")
    client = Client.objects.create(id=actor)
    Entreprise.objects.create(id=client, nom="Client Démo")
    return client


@pytest.fixture
def invoice(db, project, supplier, client_entity):
    return Facture.objects.create(
        id="FAC-001",
        numero_facture="FA-2026-001",
        societe="Benjamin Immobilier",
        affaire="Affaire Démo",
        dossier=project,
        fournisseur=supplier,
        client=client_entity,
        montant=1234.5,
        statut="ongoing",
        service="financier",
        echeance=timezone.now() + timedelta(days=3),
        titre="Facture énergie",
    )


def configure_gmail_sender(user):
    OAuthToken.objects.create(
        user=user,
        provider="google",
        email=user.email,
        access_token="access",
        refresh_token="refresh",
        token_expiry=timezone.now() + timedelta(hours=1),
    )
    InvoiceReminderSettings.objects.create(sender=user)


@pytest.mark.django_db
def test_cegid_line_is_ascii_and_deterministic(invoice):
    line = build_cegid_line(invoice)

    line.encode("ascii")
    assert line == "FAC-001;FA-2026-001;Benjamin Immobilier;Affaire Demo;financier;TECH-001 - Projet Test;Fournisseur Energie;1234.50;ongoing;" + invoice.echeance.strftime("%Y%m%d") + ";Facture energie"


@pytest.mark.django_db
def test_generate_cegid_export_creates_successful_run(finance_user, invoice):
    run = generate_cegid_export(user=finance_user)

    assert run.status == "success"
    assert run.line_count == 1
    assert run.total_amount == 1234.5
    assert run.file.name.endswith(".txt")
    assert run.file.read().decode("ascii").startswith("FAC-001;FA-2026-001;Benjamin Immobilier;Affaire Demo;financier;")


@pytest.mark.django_db
def test_invoice_anomalies_detect_missing_amount_and_overdue(invoice):
    invoice.montant = None
    invoice.echeance = timezone.now() - timedelta(days=1)
    invoice.save()

    kinds = {item["kind"] for item in get_invoice_anomalies()}

    assert "missing_amount" in kinds
    assert "overdue_open" in kinds


@pytest.mark.django_db
def test_invoice_reminder_sends_once_per_day(invoice, supplier, finance_user):
    configure_gmail_sender(finance_user)
    invoice.echeance = timezone.now() - timedelta(days=4)
    invoice.save(update_fields=["echeance"])
    RelanceFournisseur.objects.create(id="default", message="Facture {facture_id}", temps=3)
    contact = Contact.objects.create(id="CONTACT-1", acteur=supplier.id, nom="Contact")
    EmailFournisseur.objects.create(contact=contact, email="supplier@example.com")

    with patch(
        "invoices.tasks.send_message",
        return_value={"success": True, "message_id": "gmail-finance"},
    ):
        first = check_and_send_invoice_reminders()
        second = check_and_send_invoice_reminders()

    assert first["relances_envoyees"] == 1
    assert second["relances_envoyees"] == 0
    assert FactureHistorique.objects.filter(facture=invoice, action="reminder_sent").count() == 1


@pytest.mark.django_db
def test_invoice_reminder_records_missing_supplier_email(invoice, finance_user):
    configure_gmail_sender(finance_user)
    invoice.echeance = timezone.now() - timedelta(days=4)
    invoice.save(update_fields=["echeance"])
    RelanceFournisseur.objects.create(id="default", message="Facture {facture_id}", temps=3)

    result = check_and_send_invoice_reminders()

    assert result["relances_envoyees"] == 0
    assert FactureHistorique.objects.filter(facture=invoice, action="reminder_skipped").exists()


@pytest.mark.django_db
def test_average_processing_days_uses_history(invoice):
    invoice.statut = "paid"
    invoice.save()
    start = FactureHistorique.objects.create(
        facture=invoice,
        action="user_action",
        new_status="ongoing",
    )
    paid = FactureHistorique.objects.create(
        facture=invoice,
        action="status_change",
        old_status="ongoing",
        new_status="paid",
    )
    FactureHistorique.objects.filter(pk=start.pk).update(created_at=timezone.now() - timedelta(days=4))
    FactureHistorique.objects.filter(pk=paid.pk).update(created_at=timezone.now())

    average = DashboardView()._average_processing_days(Facture.objects.all())

    assert round(average) == 4
