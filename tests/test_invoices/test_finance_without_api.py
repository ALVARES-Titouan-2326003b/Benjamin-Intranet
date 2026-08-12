from datetime import date, timedelta
from io import BytesIO

import pytest
from pypdf import PdfReader
from django.contrib.auth.models import Group, User
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from invoices.models import (
    ActeurExterne,
    Client,
    Entreprise,
    Facture,
    Fournisseur,
    PieceJointe,
    Societe,
)
from invoices.services.quality import get_invoice_anomalies
from invoices.services.email import send_invoice_submission_email
from invoices.views_dashboard import DashboardView
from technique.models import DocumentTechnique, TechnicalProject
from user_access.user_test_functions import can_change_facture_status


@pytest.fixture
def finance_user(db):
    group, _ = Group.objects.get_or_create(name="POLE_FINANCIER")
    user = User.objects.create_user(username="finance", email="finance@example.com")
    user.groups.add(group)
    return user


@pytest.fixture
def project(db, societe):
    return TechnicalProject.objects.create(
        reference="TECH-001",
        name="Projet Test",
        societe=societe,
    )


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
def invoice(db, project, supplier, client_entity, societe):
    return Facture.objects.create(
        id="FAC-001",
        numero_facture="FA-2026-001",
        societe=societe,
        affaire="Affaire Démo",
        dossier=project,
        fournisseur=supplier,
        client=client_entity,
        montant=1234.5,
        statut="received",
        service="financier",
        echeance=timezone.now() + timedelta(days=3),
        titre="Facture énergie",
    )


def invoice_payload(project, societe, **overrides):
    payload = {
        "fournisseur_input": "Fournisseur formulaire",
        "numero_facture": "FA-FORM-001",
        "societe": societe.pk,
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
def test_invoice_submission_email_contains_invoice_file(
    invoice, finance_user, settings, tmp_path
):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.DEFAULT_FROM_EMAIL = "intranet@example.com"
    settings.SITE_URL = "https://intranet.example.test"
    settings.MEDIA_ROOT = tmp_path
    mail.outbox = []
    PieceJointe.objects.create(
        facture=invoice,
        fichier=SimpleUploadedFile(
            "facture-2026.pdf",
            b"%PDF-1.4 facture de test",
            content_type="application/pdf",
        ),
    )

    assert send_invoice_submission_email(invoice) is True
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [finance_user.email]
    assert len(mail.outbox[0].attachments) == 1
    attachment = mail.outbox[0].attachments[0]
    assert attachment[0] == "facture-2026.pdf"
    assert attachment[1] == b"%PDF-1.4 facture de test"
    assert attachment[2] == "application/pdf"


@pytest.mark.django_db
def test_invoice_submission_email_is_not_sent_without_invoice_file(
    invoice, finance_user, settings
):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    mail.outbox = []

    assert send_invoice_submission_email(invoice) is False
    assert mail.outbox == []


@pytest.mark.django_db
def test_invoice_anomalies_detect_missing_amount_and_overdue(invoice):
    invoice.montant = None
    invoice.echeance = timezone.now() - timedelta(days=1)
    invoice.save()

    kinds = {item["kind"] for item in get_invoice_anomalies()}

    assert "missing_amount" in kinds
    assert "overdue_open" in kinds


@pytest.mark.django_db
def test_average_pending_days_uses_submission_date(invoice):
    invoice.statut = "pending"
    invoice.date_soumission = timezone.now() - timedelta(days=4)
    invoice.save(update_fields=["statut", "date_soumission"])

    average = DashboardView()._average_pending_days(Facture.objects.all())

    assert round(average) == 4


@pytest.mark.django_db
def test_finance_dashboard_groups_invoices_by_company_and_project(client, finance_user, invoice, supplier, client_entity, societe):
    other_company = Societe.objects.create(nom="Autre Société")
    project_2 = TechnicalProject.objects.create(
        reference="TECH-002",
        name="Projet Second",
        societe=other_company,
    )
    Facture.objects.create(
        id="FAC-002",
        numero_facture="FA-2026-002",
        societe=societe,
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
        societe=other_company,
        affaire=str(project_2),
        dossier=project_2,
        fournisseur=supplier,
        client=client_entity,
        montant=300,
        statut="pending",
        service="promotion",
        echeance=timezone.now() + timedelta(days=10),
        priorite="normal",
        titre="Facture en attente",
    )
    Facture.objects.create(
        id="FAC-004",
        numero_facture="FA-2026-004",
        societe=None,
        affaire="Sans dossier",
        dossier=None,
        fournisseur=supplier,
        client=client_entity,
        montant=50,
        statut="received",
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
    assert alert_counts["Dossiers avec factures en retard"] == 1
    assert f"/finance/?societe={societe.pk}".encode() in response.content
    assert b"/finance/?dossier=TECH-001" in response.content
    assert f"/pole-technique/dossiers/{invoice.dossier.pk}/".encode() in response.content


@pytest.mark.django_db
def test_finance_dashboard_filters_company_and_project(client, finance_user, invoice, supplier, client_entity):
    other_company = Societe.objects.create(nom="Autre Société")
    project_2 = TechnicalProject.objects.create(
        reference="TECH-002",
        name="Projet Second",
        societe=other_company,
    )
    Facture.objects.create(
        id="FAC-002",
        numero_facture="FA-2026-002",
        societe=other_company,
        affaire=str(project_2),
        dossier=project_2,
        fournisseur=supplier,
        client=client_entity,
        montant=300,
        statut="pending",
        service="promotion",
        echeance=timezone.now() + timedelta(days=10),
        priorite="normal",
        titre="Facture en attente",
    )
    client.force_login(finance_user)

    response = client.get("/finance/dashboard/", {"societe": "Benjamin", "dossier": "TECH-001"})

    assert response.status_code == 200
    assert response.context["kpi"]["total_count"] == 1
    assert response.context["company_rows"][0]["societe"] == "Benjamin Immobilier"
    assert response.context["project_rows"][0]["dossier__reference"] == "TECH-001"
    assert b"Autre Soci" not in response.content


@pytest.mark.django_db
def test_finance_dashboard_rankings_are_limited_to_top_five(
    client, finance_user, client_entity
):
    for index in range(6):
        actor = ActeurExterne.objects.create(id=f"SUP-TOP-{index}")
        supplier = Fournisseur.objects.create(id=actor, nom=f"Fournisseur {index}")
        company = Societe.objects.create(nom=f"Société {index}")
        project = TechnicalProject.objects.create(
            reference=f"TOP-{index}",
            name=f"Projet {index}",
            societe=company,
        )
        Facture.objects.create(
            id=f"FAC-TOP-{index}",
            numero_facture=f"TOP-{index}",
            societe=company,
            affaire=str(project),
            dossier=project,
            fournisseur=supplier,
            client=client_entity,
            montant=100 + index,
            statut="received",
            echeance=timezone.now() + timedelta(days=10),
            titre=f"Facture top {index}",
        )

    client.force_login(finance_user)
    response = client.get("/finance/dashboard/")

    assert response.status_code == 200
    assert len(response.context["company_rows"]) == 5
    assert len(response.context["project_rows"]) == 5
    assert len(response.context["top_suppliers"]) == 5
    assert "Top 5 par montant total" in response.content.decode()
    assert "Top 5 fournisseurs" in response.content.decode()


@pytest.mark.django_db
def test_finance_company_management_url_redirects_to_administrative_module(
    client, finance_user
):
    client.force_login(finance_user)

    response = client.post(
        "/finance/societes/",
        {"nom": "Nouvelle Foncière", "is_active": "on"},
    )

    assert response.status_code == 302
    assert response.url == "/administratif/societes/"
    assert not Societe.objects.filter(nom="Nouvelle Foncière").exists()


@pytest.mark.django_db
def test_administratif_can_view_company_related_content(
    client, invoice, societe, project
):
    group, _ = Group.objects.get_or_create(name="POLE_ADMINISTRATIF")
    user = User.objects.create_user(username="admin-company-detail")
    user.groups.add(group)
    project.societe = societe
    project.save(update_fields=["societe"])
    document = DocumentTechnique.objects.create(
        project=project,
        titre="Promesse de vente",
        fichier="documents_tech/promesse.pdf",
    )
    client.force_login(user)

    response = client.get(f"/administratif/societes/{societe.pk}/details/")

    assert response.status_code == 200
    assert list(response.context["invoices"]) == [invoice]
    assert list(response.context["dossiers"]) == [project]
    assert list(response.context["documents"]) == [document]
    content = response.content.decode()
    assert "FA-2026-001" in content
    assert "TECH-001" in content
    assert "Promesse de vente" in content


@pytest.mark.django_db
def test_invoice_company_filter_uses_registered_companies(client, finance_user, invoice, societe):
    client.force_login(finance_user)

    response = client.get("/finance/", {"societe": societe.pk})

    assert response.status_code == 200
    content = response.content.decode()
    assert '<select name="societe"' in content
    assert f'value="{societe.pk}" selected' in content
    assert list(response.context["filter"].qs) == [invoice]


@pytest.mark.django_db
def test_invoice_affaire_filter_also_searches_linked_dossiers(
    client,
    finance_user,
    invoice,
):
    invoice.affaire = "Libellé historique sans référence"
    invoice.save(update_fields=["affaire"])
    client.force_login(finance_user)

    response = client.get("/finance/", {"affaire": invoice.dossier.reference})

    assert response.status_code == 200
    assert list(response.context["filter"].qs) == [invoice]


@pytest.mark.django_db
def test_invoice_list_renders_stable_status_and_date_cells(client, finance_user, invoice):
    invoice.statut = "pending"
    invoice.save(update_fields=["statut"])
    client.force_login(finance_user)

    response = client.get("/finance/")

    assert response.status_code == 200
    content = response.content.decode()
    assert 'class="table invoice-table"' in content
    assert 'class="invoice-table__status-cell"' in content
    assert 'class="invoice-status invoice-status--pending"' in content
    assert 'class="invoice-table__date-cell"' in content


@pytest.mark.django_db
def test_invoice_pdf_export_fits_all_columns_on_landscape_page(
    client,
    finance_user,
    invoice,
):
    invoice.dossier.name = "Une résidence avec un nom volontairement très long"
    invoice.dossier.save(update_fields=["name"])
    invoice.fournisseur.nom = "Un fournisseur au nom particulièrement long"
    invoice.fournisseur.save(update_fields=["nom"])
    client.force_login(finance_user)

    response = client.get("/finance/", {"export": "pdf"})

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    reader = PdfReader(BytesIO(response.content))
    first_page = reader.pages[0]
    assert float(first_page.mediabox.width) > float(first_page.mediabox.height)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "Dossier / affaire" in text
    assert "Pôle" in text
    assert "Fournisseur" in text
    assert "Échéance" in text
    assert "FAC-001" in text


@pytest.mark.django_db
def test_invoice_list_is_ordered_by_most_recent_creation_date(
    client,
    finance_user,
    supplier,
    client_entity,
):
    creation_dates = (
        timezone.make_aware(timezone.datetime(2026, 1, 15, 9, 0)),
        timezone.make_aware(timezone.datetime(2026, 3, 20, 9, 0)),
        timezone.make_aware(timezone.datetime(2026, 2, 10, 9, 0)),
        timezone.make_aware(timezone.datetime(2025, 12, 1, 9, 0)),
    )
    invoices = [
        Facture.objects.create(
            id=invoice_id,
            numero_facture=invoice_id,
            fournisseur=supplier,
            client=client_entity,
            montant=100,
            date_facture=invoice_date,
            date_soumission=creation_date,
        )
        for (invoice_id, invoice_date), creation_date in zip(
            (
                ("FAC-OLDER", date(2026, 4, 15)),
                ("FAC-NEWEST", date(2025, 11, 20)),
                ("FAC-MIDDLE", date(2026, 5, 10)),
                ("FAC-WITHOUT-DATE", None),
            ),
            creation_dates,
        )
    ]
    client.force_login(finance_user)

    response = client.get("/finance/")

    assert response.status_code == 200
    assert list(response.context["object_list"]) == [
        invoices[1],
        invoices[2],
        invoices[0],
        invoices[3],
    ]


@pytest.mark.django_db
def test_invoice_list_is_paginated_and_preserves_filters(
    client,
    finance_user,
    supplier,
    client_entity,
):
    Facture.objects.bulk_create(
        [
            Facture(
                id=f"FAC-PAGE-{index:02d}",
                numero_facture=f"PAGE-{index:02d}",
                fournisseur=supplier,
                client=client_entity,
                montant=index,
            )
            for index in range(45)
        ]
    )
    client.force_login(finance_user)

    response = client.get(
        "/finance/",
        {"numero_facture": "PAGE", "page": 2},
    )

    assert response.status_code == 200
    assert response.context["page_obj"].number == 2
    assert response.context["page_obj"].paginator.count == 45
    assert len(response.context["object_list"]) == 20
    assert response.context["invoice_query_params"] == "numero_facture=PAGE"

    content = response.content.decode()
    assert "Factures 21 à 40 sur 45" in content
    assert "Page <strong>2</strong> sur 3" in content
    assert 'aria-label="Première page"' in content
    assert 'aria-label="Dernière page"' in content
    assert "?numero_facture=PAGE&amp;page=1" in content
    assert "page=2&amp;page=" not in content


@pytest.mark.django_db
def test_non_finance_user_cannot_manage_companies(client):
    group, _ = Group.objects.get_or_create(name="POLE_TECHNIQUE")
    user = User.objects.create_user(username="company-denied")
    user.groups.add(group)
    client.force_login(user)

    response = client.get("/finance/societes/")

    assert response.status_code == 302


@pytest.mark.django_db
def test_finance_dashboard_stays_finance_only(client):
    group, _ = Group.objects.get_or_create(name="POLE_TECHNIQUE")
    user = User.objects.create_user(username="technique-dashboard", email="technique-dashboard@example.com")
    user.groups.add(group)
    client.force_login(user)

    response = client.get("/finance/dashboard/")

    assert response.status_code == 302


@pytest.mark.django_db
def test_promotion_user_can_create_invoice_without_collaborateur_role(client, project, societe):
    group, _ = Group.objects.get_or_create(name="POLE_PROMOTION")
    user = User.objects.create_user(username="promotion", email="promotion@example.com")
    user.groups.add(group)
    client.force_login(user)

    response = client.post(
        "/finance/facture/new/",
        invoice_payload(
            project,
            societe,
            statut="pending",
            service="technique",
            fichier=SimpleUploadedFile(
                "facture-promotion.pdf",
                b"%PDF-1.4 facture promotion",
                content_type="application/pdf",
            ),
        ),
    )

    assert response.status_code == 302
    facture = Facture.objects.get(numero_facture="FA-FORM-001")
    assert facture.created_by == user
    assert facture.demandeur == user
    assert facture.collaborateur == user
    assert facture.statut == "received"
    assert facture.service == "technique"
    assert facture.dossier == project
    assert facture.affaire == "TECH-001 - Projet Test"


@pytest.mark.django_db
def test_invoice_creation_notifies_finance_and_ceo(
    client, project, settings, societe, tmp_path
):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.DEFAULT_FROM_EMAIL = "intranet@example.com"
    settings.SITE_URL = "https://intranet.example.test"
    settings.MEDIA_ROOT = tmp_path
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
        invoice_payload(
            project,
            societe,
            numero_facture="FA-NOTIF-001",
            fichier=SimpleUploadedFile(
                "facture-notification.pdf",
                b"%PDF-1.4 facture notification",
                content_type="application/pdf",
            ),
        ),
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
    assert "Pôle : Promotion" in email.body
    assert "Lien intranet : https://intranet.example.test/finance/facture/" in email.body
    assert len(email.attachments) == 1
    assert email.attachments[0][0] == "facture-notification.pdf"


@pytest.mark.django_db
def test_administratif_user_can_view_invoice_overview(client, invoice):
    group, _ = Group.objects.get_or_create(name="POLE_ADMINISTRATIF")
    user = User.objects.create_user(username="admin-invoices", email="admin-invoices@example.com")
    user.groups.add(group)
    invoice.created_by = user
    invoice.save(update_fields=["created_by"])
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
    invoice.created_by = user
    invoice.save(update_fields=["created_by"])
    client.force_login(user)

    response = client.get("/finance/")

    assert response.status_code == 200
    assert b"FA-2026-001" in response.content
    assert b"Nouvelle facture" in response.content


@pytest.mark.django_db
def test_non_finance_user_cannot_view_an_invoice_they_did_not_create(client, invoice):
    group, _ = Group.objects.get_or_create(name="POLE_DEVELOPPEMENT")
    user = User.objects.create_user(username="invoice-scope", email="invoice-scope@example.com")
    user.groups.add(group)
    invoice.demandeur = user
    invoice.collaborateur = user
    invoice.save(update_fields=["demandeur", "collaborateur"])
    client.force_login(user)

    list_response = client.get("/finance/")
    detail_response = client.get(f"/finance/facture/{invoice.pk}/")
    edit_response = client.get(f"/finance/facture/{invoice.pk}/edit/")

    assert list_response.status_code == 200
    assert b"FA-2026-001" not in list_response.content
    assert detail_response.status_code == 404
    assert edit_response.status_code == 404


@pytest.mark.django_db
def test_global_search_uses_the_same_invoice_creator_scope(client, invoice):
    group, _ = Group.objects.get_or_create(name="POLE_DEVELOPPEMENT")
    user = User.objects.create_user(username="invoice-search-scope")
    user.groups.add(group)
    invoice.demandeur = user
    invoice.collaborateur = user
    invoice.save(update_fields=["demandeur", "collaborateur"])
    client.force_login(user)

    unrelated_response = client.get("/recherche/", {"q": invoice.numero_facture})
    invoice.created_by = user
    invoice.save(update_fields=["created_by"])
    owned_response = client.get("/recherche/", {"q": invoice.numero_facture})

    assert unrelated_response.status_code == 200
    assert list(unrelated_response.context["factures"]) == []
    assert owned_response.status_code == 200
    assert list(owned_response.context["factures"]) == [invoice]


@pytest.mark.django_db
def test_finance_and_superadmin_can_view_all_invoices(client, finance_user, invoice):
    client.force_login(finance_user)
    finance_response = client.get("/finance/")

    superadmin = User.objects.create_superuser(
        username="invoice-superadmin",
        email="invoice-superadmin@example.com",
        password="testpass123",
    )
    client.force_login(superadmin)
    superadmin_response = client.get("/finance/")

    assert finance_response.status_code == 200
    assert superadmin_response.status_code == 200
    assert b"FA-2026-001" in finance_response.content
    assert b"FA-2026-001" in superadmin_response.content


@pytest.mark.django_db
def test_non_finance_user_cannot_forge_invoice_status_update(client, invoice, societe):
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
            societe,
            fournisseur_input=invoice.fournisseur_id,
            numero_facture=invoice.numero_facture,
            statut="pending",
            service="developpement",
        ),
    )

    assert response.status_code == 302
    invoice.refresh_from_db()
    assert invoice.statut == "received"
    assert invoice.service == "developpement"


@pytest.mark.django_db
def test_finance_user_can_change_invoice_status(client, finance_user, invoice, societe):
    client.force_login(finance_user)

    response = client.post(
        f"/finance/facture/{invoice.pk}/edit/",
        {
            **invoice_payload(
                invoice.dossier,
                societe,
                fournisseur_input=invoice.fournisseur_id,
                numero_facture=invoice.numero_facture,
                service="financier",
            ),
            "statut": "pending",
        },
    )

    assert response.status_code == 302
    invoice.refresh_from_db()
    assert invoice.statut == "pending"
