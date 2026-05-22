from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone

from invoices.models import ActeurExterne, Client, Facture, Fournisseur
from technique.models import (
    ProjectExpense,
    TechnicalEmail,
    TechnicalProject,
    TechnicalProjectHistory,
)


@pytest.fixture
def technique_group(db):
    return Group.objects.get_or_create(name="POLE_TECHNIQUE")[0]


@pytest.fixture
def technique_user(user_factory, technique_group):
    user = user_factory(username="tech_user", email="tech@example.com")
    user.groups.add(technique_group)
    return user


@pytest.fixture
def other_technique_user(user_factory, technique_group):
    user = user_factory(username="other_tech", email="other@example.com")
    user.groups.add(technique_group)
    return user


@pytest.fixture
def project(db):
    return TechnicalProject.objects.create(
        reference="TECH-001",
        name="Projet Technique",
        type="client",
        total_estimated=Decimal("1000.00"),
    )


@pytest.fixture
def actors(db):
    supplier_actor = ActeurExterne.objects.create(id="FOUR-001")
    client_actor = ActeurExterne.objects.create(id="CLI-001")
    return {
        "supplier": Fournisseur.objects.create(id=supplier_actor, nom="Alpha BTP"),
        "client": Client.objects.create(id=client_actor),
    }


def create_invoice(project, actors, invoice_id, supplier_name="Alpha BTP", status="ongoing", due=None):
    supplier = actors["supplier"]
    if supplier_name != supplier.nom:
        supplier_actor = ActeurExterne.objects.create(id=f"FOUR-{invoice_id}")
        supplier = Fournisseur.objects.create(id=supplier_actor, nom=supplier_name)

    return Facture.objects.create(
        id=invoice_id,
        dossier=project,
        fournisseur=supplier,
        client=actors["client"],
        montant=100,
        statut=status,
        echeance=due or timezone.datetime(2026, 5, 20, tzinfo=timezone.get_current_timezone()),
        titre=f"Facture {invoice_id}",
    )


@pytest.mark.django_db
def test_email_detail_is_limited_to_importing_user(client, technique_user, other_technique_user):
    email = TechnicalEmail.objects.create(
        subject="Email privé",
        sender="sender@example.com",
        body="Contenu",
        received_at=timezone.now(),
        imported_by=other_technique_user,
    )

    client.force_login(technique_user)
    response = client.get(reverse("technique:mail_detail", args=[email.pk]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_email_actions_are_limited_to_importing_user(client, technique_user, other_technique_user, project):
    email = TechnicalEmail.objects.create(
        subject="Email privé",
        sender="sender@example.com",
        body="Contenu",
        received_at=timezone.now(),
        imported_by=other_technique_user,
    )

    client.force_login(technique_user)
    assign_response = client.post(
        reverse("technique:mail_assign_project", args=[email.pk]),
        {"project_id": project.pk},
    )

    assert assign_response.status_code == 404
    email.refresh_from_db()
    assert email.project is None
    assert email.status == "unassigned"

    with patch("technique.services.ai_classify.classify_and_save") as classify_mock:
        classify_response = client.post(reverse("technique:email_classify", args=[email.pk]))

    assert classify_response.status_code == 404
    classify_mock.assert_not_called()


@pytest.mark.django_db
def test_bulk_email_classification_only_processes_current_user_emails(
    client,
    technique_user,
    other_technique_user,
    project,
):
    owned_email = TechnicalEmail.objects.create(
        subject="Email utilisateur",
        sender="sender@example.com",
        body="Contenu",
        received_at=timezone.now(),
        imported_by=technique_user,
    )
    other_email = TechnicalEmail.objects.create(
        subject="Email autre utilisateur",
        sender="sender@example.com",
        body="Contenu",
        received_at=timezone.now(),
        imported_by=other_technique_user,
    )

    def fake_classify(email, projects, sleep=0):
        email.project = project
        email.status = "classified"
        email.save(update_fields=["project", "status"])
        return {"success": True, "saved": True, "project_id": project.pk, "confidence": "high"}

    client.force_login(technique_user)
    with patch("technique.services.ai_classify.classify_and_save", side_effect=fake_classify) as classify_mock:
        response = client.post(reverse("technique:email_classify_bulk"))

    assert response.status_code == 200
    assert classify_mock.call_count == 1
    assert classify_mock.call_args.args[0].pk == owned_email.pk
    other_email.refresh_from_db()
    assert other_email.status == "unassigned"
    assert other_email.project is None


@pytest.mark.django_db
def test_financial_history_is_created_for_project_budget_and_expense_changes(
    client,
    technique_user,
    project,
    actors,
):
    client.force_login(technique_user)
    overview_url = reverse("technique:technique_financial_overview")

    response = client.post(
        overview_url,
        {
            "name": "Nouveau Projet",
            "reference": "TECH-NEW",
            "type": "client",
            "total_estimated": "500.00",
        },
    )
    assert response.status_code == 302
    new_project = TechnicalProject.objects.get(reference="TECH-NEW")
    assert TechnicalProjectHistory.objects.filter(
        project=new_project,
        action="project_created",
        user=technique_user,
    ).exists()

    detail_url = reverse("technique:technique_financial_project_detail", args=[project.pk])
    response = client.post(detail_url, {"total_estimated": "1500.00"})
    assert response.status_code == 302
    assert TechnicalProjectHistory.objects.filter(project=project, action="budget_updated").exists()

    invoice = create_invoice(project, actors, "FAC-HIST")
    create_url = reverse("technique:technique_project_expense_create", args=[project.pk])
    response = client.post(
        create_url,
        {
            "facture": invoice.pk,
            "label": "Honoraires",
            "amount": "250.00",
            "is_paid": "on",
            "due_date": "2026-05-20",
            "payment_date": "2026-05-21",
        },
    )
    assert response.status_code == 302
    expense = ProjectExpense.objects.get(label="Honoraires")
    assert TechnicalProjectHistory.objects.filter(project=project, action="expense_created").exists()

    update_url = reverse("technique:technique_project_expense_update", args=[expense.pk])
    response = client.post(
        update_url,
        {
            "facture": invoice.pk,
            "label": "Honoraires actualisés",
            "amount": "300.00",
            "due_date": "2026-05-22",
        },
    )
    assert response.status_code == 302
    assert TechnicalProjectHistory.objects.filter(project=project, action="expense_updated").exists()

    delete_url = reverse("technique:technique_project_expense_delete", args=[expense.pk])
    response = client.post(delete_url)
    assert response.status_code == 302
    assert TechnicalProjectHistory.objects.filter(project=project, action="expense_deleted").exists()


@pytest.mark.django_db
def test_project_deletion_history_keeps_snapshot_after_project_is_deleted(client, technique_user):
    project = TechnicalProject.objects.create(reference="DEL-001", name="Projet à supprimer")

    client.force_login(technique_user)
    response = client.post(
        reverse("technique:bulk_delete_projects"),
        {"project_ids": [project.pk]},
    )

    assert response.status_code == 302
    history = TechnicalProjectHistory.objects.get(action="project_deleted", project_reference="DEL-001")
    assert history.project is None
    assert history.project_name == "Projet à supprimer"


@pytest.mark.django_db
def test_invoice_filters_on_financial_project_detail(client, technique_user, project, actors):
    linked_invoice = create_invoice(
        project,
        actors,
        "FAC-LINK",
        supplier_name="Alpha BTP",
        status="paid",
        due=timezone.datetime(2026, 5, 10, tzinfo=timezone.get_current_timezone()),
    )
    unlinked_invoice = create_invoice(
        project,
        actors,
        "FAC-FILTER",
        supplier_name="Beta Travaux",
        status="ongoing",
        due=timezone.datetime(2026, 6, 10, tzinfo=timezone.get_current_timezone()),
    )
    ProjectExpense.objects.create(
        project=project,
        facture=linked_invoice,
        label="Dépense liée",
        amount=Decimal("100.00"),
        is_paid=True,
        due_date=date(2026, 5, 10),
    )

    client.force_login(technique_user)
    response = client.get(
        reverse("technique:technique_financial_project_detail", args=[project.pk]),
        {
            "invoice_supplier": "Beta",
            "invoice_status": "ongoing",
            "invoice_due_from": "2026-06-01",
            "invoice_due_to": "2026-06-30",
            "invoice_association": "unlinked",
        },
    )

    assert response.status_code == 200
    invoices = list(response.context["project_invoices"])
    assert invoices == [unlinked_invoice]


@pytest.mark.django_db
def test_financial_calculations_and_exports_still_work(client, technique_user, project, actors):
    create_invoice(project, actors, "FAC-EXPORT")
    ProjectExpense.objects.create(
        project=project,
        label="Payé",
        amount=Decimal("200.00"),
        is_paid=True,
        due_date=date(2026, 5, 20),
    )
    ProjectExpense.objects.create(
        project=project,
        label="À payer",
        amount=Decimal("100.00"),
        is_paid=False,
        due_date=date(2026, 5, 21),
    )
    project.refresh_from_db()

    assert project.frais_engages == Decimal("300.00")
    assert project.frais_payes == Decimal("200.00")
    assert project.frais_restants == Decimal("100.00")
    assert project.reste_a_engager == Decimal("700.00")

    client.force_login(technique_user)
    for url_name in (
        "technique_financial_project_pdf",
        "technique_financial_project_csv",
        "technique_financial_project_excel",
    ):
        response = client.get(reverse(f"technique:{url_name}", args=[project.pk]))
        assert response.status_code == 200
        assert response.content
