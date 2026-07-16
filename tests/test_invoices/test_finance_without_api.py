from datetime import timedelta

import pytest
from django.contrib.auth.models import Group, User
from django.core import mail
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
from invoices.services.quality import get_invoice_anomalies
from invoices.tasks import check_and_send_invoice_reminders
from invoices.views_dashboard import DashboardView
from technique.models import TechnicalProject
from user_access.user_test_functions import can_change_facture_status


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


def invoice_payload(project, **overrides):
    payload = {
        "fournisseur_input": "Fournisseur formulaire",
        "numero_facture": "FA-FORM-001",
        "societe": "Benjamin Immobilier",
        "affaire": "Affaire formulaire",
        "dossier": project.pk,
        "montant": "450.00",
        "service": "promotion",
        "priorite": "normal",
        "titre": "Facture formulaire",
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
def test_legacy_ceo_group_cannot_change_invoice_status_without_superadmin_rights():
    ceo_group, _ = Group.objects.get_or_create(name="CEO")
    ceo = User.objects.create_user(username="ceo", email="ceo@example.com")
    ceo.groups.add(ceo_group)

    assert can_change_facture_status(ceo) is False


@pytest.mark.django_db
def test_site_admin_can_change_invoice_status_without_ceo_group():
    admin = User.objects.create_superuser(
        username="administrateur",
        email="admin@example.com",
        password="adminpass",
    )

    assert can_change_facture_status(admin) is True


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


@pytest.mark.django_db
def test_finance_dashboard_groups_invoices_by_company_and_project(client, finance_user, invoice, supplier, client_entity):
    project_2 = TechnicalProject.objects.create(reference="TECH-002", name="Projet Second")
    Facture.objects.create(
        id="FAC-002",
        numero_facture="FA-2026-002",
        societe="Benjamin Immobilier",
        affaire="Ancien libellé",
        dossier=invoice.dossier,
        fournisseur=supplier,
        client=client_entity,
        montant=1000,
        statut="received",
        service="technique",
        echeance=timezone.now() - timedelta(days=2),
        priorite="urgent",
        titre="Facture en retard",
    )
    Facture.objects.create(
        id="FAC-003",
        numero_facture="FA-2026-003",
        societe="Autre Société",
        affaire=str(project_2),
        dossier=project_2,
        fournisseur=supplier,
        client=client_entity,
        montant=300,
        statut="paid",
        service="promotion",
        echeance=timezone.now() + timedelta(days=10),
        priorite="normal",
        titre="Facture payée",
    )
    Facture.objects.create(
        id="FAC-004",
        numero_facture="FA-2026-004",
        societe="",
        affaire="Sans dossier",
        dossier=None,
        fournisseur=supplier,
        client=client_entity,
        montant=50,
        statut="ongoing",
        service="administratif",
        echeance=timezone.now() + timedelta(days=5),
        priorite="normal",
        titre="Facture incomplète",
    )
    client.force_login(finance_user)

    response = client.get("/finance/dashboard/")

    assert response.status_code == 200
    company_rows = {row["societe"]: row for row in response.context["company_rows"]}
    assert company_rows["Benjamin Immobilier"]["count"] == 2
    assert company_rows["Benjamin Immobilier"]["total"] == 2234.5
    assert company_rows["Benjamin Immobilier"]["overdue_total"] == 1000

    project_rows = {row["dossier__reference"]: row for row in response.context["project_rows"]}
    assert project_rows["TECH-001"]["open_count"] == 2
    assert project_rows["TECH-001"]["urgent_count"] == 1
    assert project_rows["TECH-001"]["overdue_count"] == 1

    alert_counts = {alert["label"]: alert["count"] for alert in response.context["business_alerts"]}
    assert alert_counts["Factures sans société"] == 1
    assert alert_counts["Factures sans dossier"] == 1
    assert alert_counts["Affaire différente du dossier lié"] == 2
    assert alert_counts["Dossiers avec factures en retard"] == 1
    assert b"/finance/?societe=Benjamin+Immobilier" in response.content
    assert b"/finance/?dossier=TECH-001" in response.content
    assert f"/pole-technique/dossiers/{invoice.dossier.pk}/".encode() in response.content


@pytest.mark.django_db
def test_finance_dashboard_filters_company_and_project(client, finance_user, invoice, supplier, client_entity):
    project_2 = TechnicalProject.objects.create(reference="TECH-002", name="Projet Second")
    Facture.objects.create(
        id="FAC-002",
        numero_facture="FA-2026-002",
        societe="Autre Société",
        affaire=str(project_2),
        dossier=project_2,
        fournisseur=supplier,
        client=client_entity,
        montant=300,
        statut="paid",
        service="promotion",
        echeance=timezone.now() + timedelta(days=10),
        priorite="normal",
        titre="Facture payée",
    )
    client.force_login(finance_user)

    response = client.get("/finance/dashboard/", {"societe": "Benjamin", "dossier": "TECH-001"})

    assert response.status_code == 200
    assert response.context["kpi"]["total_count"] == 1
    assert response.context["company_rows"][0]["societe"] == "Benjamin Immobilier"
    assert response.context["project_rows"][0]["dossier__reference"] == "TECH-001"
    assert b"Autre Soci" not in response.content


@pytest.mark.django_db
def test_finance_dashboard_stays_finance_only(client):
    group, _ = Group.objects.get_or_create(name="POLE_TECHNIQUE")
    user = User.objects.create_user(username="technique-dashboard", email="technique-dashboard@example.com")
    user.groups.add(group)
    client.force_login(user)

    response = client.get("/finance/dashboard/")

    assert response.status_code == 302


@pytest.mark.django_db
def test_promotion_user_can_create_invoice_without_collaborateur_role(client, project):
    group, _ = Group.objects.get_or_create(name="POLE_PROMOTION")
    user = User.objects.create_user(username="promotion", email="promotion@example.com")
    user.groups.add(group)
    client.force_login(user)

    response = client.post(
        "/finance/facture/new/",
        invoice_payload(project, statut="paid"),
    )

    assert response.status_code == 302
    facture = Facture.objects.get(numero_facture="FA-FORM-001")
    assert facture.created_by == user
    assert facture.demandeur == user
    assert facture.collaborateur == user
    assert facture.statut == "ongoing"
    assert facture.service == "promotion"
    assert facture.dossier == project
    assert facture.affaire == "TECH-001 - Projet Test"


@pytest.mark.django_db
def test_invoice_creation_notifies_finance_and_ceo(client, project, settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.DEFAULT_FROM_EMAIL = "intranet@example.com"
    settings.SITE_URL = "https://intranet.example.test"
    mail.outbox = []

    finance_group, _ = Group.objects.get_or_create(name="POLE_FINANCIER")
    ceo_group, _ = Group.objects.get_or_create(name="CEO")
    promotion_group, _ = Group.objects.get_or_create(name="POLE_PROMOTION")

    finance = User.objects.create_user(username="finance-notif", email="finance-notif@example.com")
    ceo = User.objects.create_user(username="ceo-notif", email="ceo-notif@example.com")
    requester = User.objects.create_user(username="promotion-notif", email="promotion-notif@example.com")
    finance.groups.add(finance_group)
    ceo.groups.add(ceo_group)
    requester.groups.add(promotion_group)
    client.force_login(requester)

    response = client.post(
        "/finance/facture/new/",
        invoice_payload(project, numero_facture="FA-NOTIF-001"),
    )

    assert response.status_code == 302
    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    assert set(email.to) == {"finance-notif@example.com", "ceo-notif@example.com"}
    assert "Nouvelle facture transmise : FA-NOTIF-001" == email.subject
    assert "Fournisseur : Fournisseur formulaire" in email.body
    assert "Numéro de facture : FA-NOTIF-001" in email.body
    assert "Société : Benjamin Immobilier" in email.body
    assert "Dossier / affaire : TECH-001 - Projet Test" in email.body
    assert "Montant TTC : 450.0 €" in email.body
    assert "Demandeur : promotion-notif" in email.body
    assert "Service / pôle : Promotion" in email.body
    assert "Lien intranet : https://intranet.example.test/finance/facture/" in email.body


@pytest.mark.django_db
def test_administratif_user_can_view_invoice_overview(client, invoice):
    group, _ = Group.objects.get_or_create(name="POLE_ADMINISTRATIF")
    user = User.objects.create_user(username="admin-invoices", email="admin-invoices@example.com")
    user.groups.add(group)
    client.force_login(user)

    response = client.get("/finance/")

    assert response.status_code == 200
    assert b"FA-2026-001" in response.content
    assert b"Nouvelle facture" in response.content


@pytest.mark.django_db
def test_technique_user_can_view_invoice_overview(client, invoice):
    group, _ = Group.objects.get_or_create(name="POLE_TECHNIQUE")
    user = User.objects.create_user(username="technique-invoices", email="technique-invoices@example.com")
    user.groups.add(group)
    client.force_login(user)

    response = client.get("/finance/")

    assert response.status_code == 200
    assert b"FA-2026-001" in response.content
    assert b"Nouvelle facture" in response.content


@pytest.mark.django_db
def test_non_finance_user_cannot_forge_invoice_status_update(client, invoice):
    group, _ = Group.objects.get_or_create(name="POLE_DEVELOPPEMENT")
    user = User.objects.create_user(username="developpement", email="developpement@example.com")
    user.groups.add(group)
    invoice.created_by = user
    invoice.demandeur = user
    invoice.collaborateur = user
    invoice.save(update_fields=["created_by", "demandeur", "collaborateur"])
    client.force_login(user)

    response = client.post(
        f"/finance/facture/{invoice.pk}/edit/",
        invoice_payload(
            invoice.dossier,
            fournisseur_input=invoice.fournisseur_id,
            numero_facture=invoice.numero_facture,
            statut="paid",
            service="developpement",
        ),
    )

    assert response.status_code == 302
    invoice.refresh_from_db()
    assert invoice.statut == "ongoing"
    assert invoice.service == "financier"


@pytest.mark.django_db
def test_finance_user_can_change_invoice_status(client, finance_user, invoice):
    client.force_login(finance_user)

    response = client.post(
        f"/finance/facture/{invoice.pk}/edit/",
        {
            **invoice_payload(
                invoice.dossier,
                fournisseur_input=invoice.fournisseur_id,
                numero_facture=invoice.numero_facture,
                service="financier",
            ),
            "statut": "paid",
        },
    )

    assert response.status_code == 302
    invoice.refresh_from_db()
    assert invoice.statut == "paid"
