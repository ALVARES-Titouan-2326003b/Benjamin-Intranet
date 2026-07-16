from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone

from invoices.models import ActeurExterne, Client, Facture, Fournisseur
from technique.forms import TechnicalProjectActionForm
from technique.models import (
    DocumentTechnique,
    ProjectExpense,
    TechnicalEmail,
    TechnicalProject,
    TechnicalProjectAction,
    TechnicalProjectHistory,
    TechnicalProjectKeyDate,
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
def administrative_user(user_factory, db):
    group, _ = Group.objects.get_or_create(name="POLE_ADMINISTRATIF")
    user = user_factory(username="admin_pole", email="admin-pole@example.com")
    user.groups.add(group)
    return user


@pytest.fixture
def project(db):
    return TechnicalProject.objects.create(
        reference="TECH-001",
        name="Projet Technique",
        type="marchands_de_bien",
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
@pytest.mark.parametrize(
    ("activity_type", "label"),
    [
        ("marchands_de_bien", "Marchands de bien"),
        ("promotion", "Promotion"),
        ("patrimoine", "Patrimoine"),
    ],
)
def test_project_accepts_new_activity_types(activity_type, label):
    project = TechnicalProject(
        reference=f"TYPE-{activity_type}",
        name="Projet typé",
        type=activity_type,
    )

    project.full_clean()

    assert project.get_type_display() == label


@pytest.mark.django_db
def test_project_defaults_to_marchands_de_bien_and_rejects_old_type():
    project = TechnicalProject(reference="TYPE-DEFAULT", name="Projet par défaut")
    assert project.type == "marchands_de_bien"
    assert project.status == "etude"

    project.type = "client"
    with pytest.raises(ValidationError):
        project.full_clean()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("status", "label"),
    [
        ("etude", "Étude"),
        ("promesse_signee", "Promesse signée"),
        ("acquis", "Acquis"),
    ],
)
def test_project_accepts_technical_statuses(status, label):
    project = TechnicalProject(
        reference=f"STATUS-{status}",
        name="Dossier statué",
        status=status,
    )

    project.full_clean()

    assert project.get_status_display() == label


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
    overview_url = reverse("technique:dossiers_list")

    response = client.post(
        overview_url,
        {
            "name": "Nouveau Projet",
            "reference": "TECH-NEW",
            "type": "promotion",
            "status": "promesse_signee",
            "total_estimated": "500.00",
        },
    )
    assert response.status_code == 302
    new_project = TechnicalProject.objects.get(reference="TECH-NEW")
    assert new_project.type == "promotion"
    assert new_project.status == "promesse_signee"
    assert new_project.affaire == "Nouveau Projet"
    assert new_project.type_dossier == "vente"
    assert new_project.activite_metier == "marchand_biens"
    assert new_project.etat == "promesse"
    assert new_project.categorie is not None
    assert TechnicalProjectHistory.objects.filter(
        project=new_project,
        action="project_created",
        user=technique_user,
    ).exists()

    detail_url = reverse("technique:dossier_detail", args=[project.pk])
    response = client.post(detail_url, {"total_estimated": "1500.00"})
    assert response.status_code == 302
    assert TechnicalProjectHistory.objects.filter(project=project, action="budget_updated").exists()

    response = client.post(detail_url, {"update_project_status": "1", "status": "acquis"})
    assert response.status_code == 302
    project.refresh_from_db()
    assert project.status == "acquis"
    assert TechnicalProjectHistory.objects.filter(project=project, action="status_updated").exists()

    invoice = create_invoice(project, actors, "FAC-HIST")
    create_url = reverse("technique:dossier_expense_create", args=[project.pk])
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

    update_url = reverse("technique:dossier_expense_update", args=[expense.pk])
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

    delete_url = reverse("technique:dossier_expense_delete", args=[expense.pk])
    response = client.post(delete_url)
    assert response.status_code == 302
    assert TechnicalProjectHistory.objects.filter(project=project, action="expense_deleted").exists()


@pytest.mark.django_db
def test_project_expense_can_be_created_without_invoice(client, technique_user, project):
    client.force_login(technique_user)
    response = client.post(
        reverse("technique:dossier_expense_create", args=[project.pk]),
        {
            "facture": "",
            "label": "Dépense prévisionnelle",
            "amount": "180.00",
            "due_date": "2026-05-20",
        },
    )

    assert response.status_code == 302
    expense = ProjectExpense.objects.get(label="Dépense prévisionnelle")
    assert expense.facture is None
    assert expense.project == project


@pytest.mark.django_db
def test_project_actions_can_be_managed_from_project_detail(client, technique_user, project):
    client.force_login(technique_user)
    create_url = reverse("technique:dossier_action_create", args=[project.pk])

    response = client.post(
        create_url,
        {
            "title": "Relancer le géomètre",
            "assigned_to": technique_user.pk,
            "status": "in_progress",
            "priority": "urgent",
            "description": "Demander le retour du plan bornage.",
            "due_date": "2026-06-15",
        },
    )

    assert response.status_code == 302
    action = TechnicalProjectAction.objects.get(title="Relancer le géomètre")
    assert action.project == project
    assert action.assigned_to == technique_user
    assert action.created_by == technique_user
    assert TechnicalProjectHistory.objects.filter(project=project, action="action_created").exists()

    response = client.get(
        reverse("technique:dossier_detail", args=[project.pk]),
        {
            "action_q": "géomètre",
            "action_status": "in_progress",
            "action_priority": "urgent",
        },
    )

    assert response.status_code == 200
    assert list(response.context["actions"]) == [action]

    response = client.post(
        reverse("technique:dossier_action_update", args=[action.pk]),
        {
            "title": "Relancer le géomètre actualisé",
            "assigned_to": "",
            "status": "done",
            "priority": "high",
            "description": "Retour reçu.",
            "due_date": "",
        },
    )

    assert response.status_code == 302
    action.refresh_from_db()
    assert action.title == "Relancer le géomètre actualisé"
    assert action.assigned_to is None
    assert action.status == "done"
    assert action.updated_by == technique_user
    assert TechnicalProjectHistory.objects.filter(project=project, action="action_updated").exists()

    response = client.post(reverse("technique:dossier_action_delete", args=[action.pk]))

    assert response.status_code == 302
    assert not TechnicalProjectAction.objects.filter(pk=action.pk).exists()
    assert TechnicalProjectHistory.objects.filter(project=project, action="action_deleted").exists()


@pytest.mark.django_db
def test_project_actions_only_allow_technical_assignees(
    client, technique_user, project, user_factory
):
    non_technical_user = user_factory(username="finance_user", email="finance@example.com")

    form = TechnicalProjectActionForm()
    assert list(form.fields["assigned_to"].queryset) == [technique_user]

    client.force_login(technique_user)
    response = client.post(
        reverse("technique:dossier_action_create", args=[project.pk]),
        {
            "title": "Action mal assignée",
            "assigned_to": non_technical_user.pk,
            "status": "todo",
            "priority": "normal",
            "description": "",
            "due_date": "",
        },
    )

    assert response.status_code == 302
    assert not TechnicalProjectAction.objects.filter(title="Action mal assignée").exists()


@pytest.mark.django_db
def test_administrative_pole_has_read_only_technical_project_access(
    client, administrative_user, project
):
    action = TechnicalProjectAction.objects.create(project=project, title="Action visible")
    client.force_login(administrative_user)

    list_response = client.get(reverse("technique:dossiers_list"))
    assert list_response.status_code == 200
    assert list_response.context["can_manage_projects"] is False
    assert "Consultation en lecture seule" in list_response.content.decode()
    assert "Créer un dossier" not in list_response.content.decode()

    detail_response = client.get(reverse("technique:dossier_detail", args=[project.pk]))
    assert detail_response.status_code == 200
    assert detail_response.context["can_manage_project"] is False
    assert "Action visible" in detail_response.content.decode()
    assert "Ajouter l'action" not in detail_response.content.decode()

    denied_update = client.post(
        reverse("technique:dossier_detail", args=[project.pk]),
        {"update_project_status": "1", "status": "acquis"},
    )
    assert denied_update.status_code == 403

    denied_action = client.post(
        reverse("technique:dossier_action_create", args=[project.pk]),
        {"title": "Action interdite"},
    )
    assert denied_action.status_code == 302
    assert not TechnicalProjectAction.objects.filter(title="Action interdite").exists()

    assert client.get(reverse("technique:documents_list")).status_code == 302
    assert client.get(reverse("technique:dossier_budget_pdf", args=[project.pk])).status_code == 200
    assert client.get(reverse("technique:dossier_budget_excel", args=[project.pk])).status_code == 200


@pytest.mark.django_db
def test_project_key_dates_can_link_documents_and_actions(client, technique_user, project, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    client.force_login(technique_user)
    document = DocumentTechnique.objects.create(
        project=project,
        titre="Permis de construire",
        fichier=SimpleUploadedFile("permis.txt", b"permis"),
        created_by=technique_user,
    )
    action = TechnicalProjectAction.objects.create(
        project=project,
        title="Vérifier le permis",
        assigned_to=technique_user,
    )

    response = client.post(
        reverse("technique:dossier_key_date_create", args=[project.pk]),
        {
            "label": "Dépôt du permis",
            "date": "2026-06-20",
            "status": "planned",
            "comment": "Dossier à déposer en mairie.",
            "document": document.pk,
            "action": action.pk,
        },
    )

    assert response.status_code == 302
    key_date = TechnicalProjectKeyDate.objects.get(label="Dépôt du permis")
    assert key_date.project == project
    assert key_date.document == document
    assert key_date.action == action
    assert key_date.created_by == technique_user
    assert TechnicalProjectHistory.objects.filter(project=project, action="key_date_created").exists()

    response = client.get(reverse("technique:dossier_detail", args=[project.pk]))

    assert response.status_code == 200
    assert list(response.context["key_dates"]) == [key_date]

    response = client.post(
        reverse("technique:dossier_key_date_update", args=[key_date.pk]),
        {
            "label": "Dépôt du permis actualisé",
            "date": "2026-06-25",
            "status": "done",
            "comment": "Dépôt réalisé.",
            "document": "",
            "action": "",
        },
    )

    assert response.status_code == 302
    key_date.refresh_from_db()
    assert key_date.label == "Dépôt du permis actualisé"
    assert key_date.document is None
    assert key_date.action is None
    assert key_date.status == "done"
    assert key_date.updated_by == technique_user
    assert TechnicalProjectHistory.objects.filter(project=project, action="key_date_updated").exists()

    response = client.post(reverse("technique:dossier_key_date_delete", args=[key_date.pk]))

    assert response.status_code == 302
    assert not TechnicalProjectKeyDate.objects.filter(pk=key_date.pk).exists()
    assert TechnicalProjectHistory.objects.filter(project=project, action="key_date_deleted").exists()


@pytest.mark.django_db
def test_project_deletion_requires_superadmin_validation(client, technique_user, admin_user):
    project = TechnicalProject.objects.create(reference="DEL-001", name="Projet à supprimer")

    client.force_login(technique_user)
    response = client.post(
        reverse("technique:dossiers_bulk_delete"),
        {"project_ids": [project.pk]},
    )

    assert response.status_code == 302
    assert TechnicalProject.objects.filter(pk=project.pk).exists()
    assert not TechnicalProjectHistory.objects.filter(action="project_deleted", project_reference="DEL-001").exists()

    client.force_login(admin_user)
    response = client.post(
        reverse("technique:dossiers_bulk_delete"),
        {"project_ids": [project.pk]},
    )

    assert response.status_code == 302
    history = TechnicalProjectHistory.objects.get(action="project_deleted", project_reference="DEL-001")
    assert history.project is None
    assert history.project_name == "Projet à supprimer"


@pytest.mark.django_db
def test_project_deletion_with_related_data_requires_explicit_confirmation(client, admin_user):
    project = TechnicalProject.objects.create(reference="DEL-LINK", name="Dossier avec liens")
    ProjectExpense.objects.create(
        project=project,
        label="Dépense existante",
        amount=Decimal("120.00"),
    )

    client.force_login(admin_user)
    response = client.post(
        reverse("technique:dossiers_bulk_delete"),
        {"project_ids": [project.pk]},
    )

    assert response.status_code == 302
    assert TechnicalProject.objects.filter(pk=project.pk).exists()

    response = client.post(
        reverse("technique:dossiers_bulk_delete"),
        {"project_ids": [project.pk], "confirm_related": "1"},
    )

    assert response.status_code == 302
    assert not TechnicalProject.objects.filter(pk=project.pk).exists()
    assert TechnicalProjectHistory.objects.filter(action="project_deleted", project_reference="DEL-LINK").exists()


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
        reverse("technique:dossier_detail", args=[project.pk]),
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
        "dossier_budget_pdf",
        "dossier_budget_excel",
    ):
        response = client.get(reverse(f"technique:{url_name}", args=[project.pk]))
        assert response.status_code == 200
        assert response.content
