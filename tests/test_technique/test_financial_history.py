import pytest
from django.contrib.auth.models import Group, User
from django.urls import reverse

from technique.models import ProjectExpense, TechnicalProject, TechnicalProjectHistory


def _create_tech_user(client):
    group, _ = Group.objects.get_or_create(name="POLE_TECHNIQUE")
    user = User.objects.create_user(username="techuser", password="pass123")
    user.groups.add(group)
    client.force_login(user)
    return user


@pytest.mark.django_db
def test_financial_overview_project_creation_logs_history(client):
    user = _create_tech_user(client)

    response = client.post(
        reverse("technique:technique_financial_overview"),
        data={
            "name": "Projet Alpha",
            "reference": "PRJ-ALPHA",
            "type": "client",
            "total_estimated": "120000.00",
        },
    )

    assert response.status_code == 302
    project = TechnicalProject.objects.get(reference="PRJ-ALPHA")
    history = TechnicalProjectHistory.objects.get(project=project)
    assert history.action_type == "project_created"
    assert history.user == user
    assert history.new_value["reference"] == "PRJ-ALPHA"


@pytest.mark.django_db
def test_budget_update_logs_old_and_new_values(client):
    user = _create_tech_user(client)
    project = TechnicalProject.objects.create(
        reference="PRJ-BUDGET",
        name="Projet Budget",
        type="client",
        total_estimated="1000.00",
    )

    response = client.post(
        reverse("technique:technique_financial_project_detail", args=[project.pk]),
        data={"total_estimated": "2500.00"},
    )

    assert response.status_code == 302
    history = TechnicalProjectHistory.objects.filter(project=project, action_type="budget_updated").latest("id")
    assert history.user == user
    assert history.old_value["total_estimated"] == "1000.00"
    assert history.new_value["total_estimated"] == "2500.00"
    assert history.changes["total_estimated"]["old"] == "1000.00"
    assert history.changes["total_estimated"]["new"] == "2500.00"


@pytest.mark.django_db
def test_expense_create_update_delete_log_history(client):
    user = _create_tech_user(client)
    project = TechnicalProject.objects.create(
        reference="PRJ-EXP",
        name="Projet Dépenses",
        type="client",
        total_estimated="5000.00",
    )

    create_response = client.post(
        reverse("technique:technique_project_expense_create", args=[project.pk]),
        data={
            "facture": "",
            "label": "Honoraires architecte",
            "amount": "900.00",
            "is_paid": "on",
            "due_date": "2026-03-01",
            "payment_date": "2026-03-05",
        },
    )
    assert create_response.status_code == 302

    expense = ProjectExpense.objects.get(project=project, label="Honoraires architecte")
    created_history = TechnicalProjectHistory.objects.filter(project=project, action_type="expense_created").latest("id")
    assert created_history.user == user
    assert created_history.new_value["label"] == "Honoraires architecte"
    assert created_history.new_value["amount"] == "900.00"

    update_response = client.post(
        reverse("technique:technique_project_expense_update", args=[expense.pk]),
        data={
            "facture": "",
            "label": "Honoraires architecte",
            "amount": "950.00",
            "due_date": "2026-03-10",
            "payment_date": "2026-03-12",
        },
    )
    assert update_response.status_code == 302

    updated_history = TechnicalProjectHistory.objects.filter(project=project, action_type="expense_updated").latest("id")
    assert updated_history.user == user
    assert updated_history.changes["amount"]["old"] == "900.00"
    assert updated_history.changes["amount"]["new"] == "950.00"
    assert updated_history.changes["is_paid"]["old"] is True
    assert updated_history.changes["is_paid"]["new"] is False

    delete_response = client.post(
        reverse("technique:technique_project_expense_delete", args=[expense.pk]),
    )
    assert delete_response.status_code == 302

    deleted_history = TechnicalProjectHistory.objects.filter(project=project, action_type="expense_deleted").latest("id")
    assert deleted_history.user == user
    assert deleted_history.old_value["label"] == "Honoraires architecte"
    assert deleted_history.old_value["amount"] == "950.00"


@pytest.mark.django_db
def test_financial_detail_displays_history_entries(client):
    _create_tech_user(client)
    project = TechnicalProject.objects.create(
        reference="PRJ-VIEW",
        name="Projet Historique",
        type="client",
        total_estimated="3000.00",
    )
    TechnicalProjectHistory.objects.create(
        project=project,
        user=None,
        action_type="project_created",
        target_type="project",
        target_label=project.reference,
        new_value={"reference": project.reference},
        changes={"reference": {"old": None, "new": project.reference}},
        summary="Projet PRJ-VIEW créé.",
    )

    response = client.get(reverse("technique:technique_financial_project_detail", args=[project.pk]))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Historique des mises a jour" in content
    assert "Projet PRJ-VIEW créé." in content
