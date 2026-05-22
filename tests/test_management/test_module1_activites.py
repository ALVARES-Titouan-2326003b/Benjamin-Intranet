import json
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from django.utils import timezone

from management.models import (
    Activite,
    AdministrativeProject,
    HistoriqueRappelActivite,
    NotificationInterne,
    TypeActivite,
)
from management.tasks import check_and_send_activite_reminders


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username="admin_module1",
        email="admin_module1@example.com",
        password="testpass123",
    )


@pytest.fixture
def responsable(db):
    return User.objects.create_user(
        username="responsable_module1",
        email="responsable_module1@example.com",
        password="testpass123",
    )


@pytest.fixture
def dossier(db):
    return AdministrativeProject.objects.create(
        reference="ADM-001",
        name="Dossier administratif",
    )


@pytest.fixture
def type_activite(db):
    return TypeActivite.objects.create(type="Relance")


def _post_json(client, url, payload):
    return client.post(
        url,
        data=json.dumps(payload),
        content_type="application/json",
    )


@pytest.mark.django_db
def test_activity_create_update_delete_with_outlook(client, admin_user, responsable, dossier, type_activite):
    client.force_login(admin_user)
    date_value = (timezone.now() + timedelta(days=8)).replace(second=0, microsecond=0)

    payload = {
        "titre": "Relance notaire",
        "dossier": dossier.reference,
        "type": type_activite.type,
        "date": date_value.isoformat(),
        "responsable": str(responsable.pk),
        "statut": "todo",
        "priorite": "high",
        "client": "Client Test",
        "contact_externe": "notaire@example.com",
        "commentaire": "Vérifier les pièces manquantes.",
        "sync_outlook": True,
    }

    with patch("management.views.create_outlook_event", return_value={"success": True, "event_id": "evt-1"}):
        response = _post_json(client, "/api/create-activity/", payload)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    activity = Activite.objects.get(pk=data["activity_id"])
    assert activity.titre == "Relance notaire"
    assert activity.responsable == responsable
    assert activity.priorite == "high"
    assert activity.outlook_event_id == "evt-1"

    update_payload = {
        **payload,
        "titre": "Relance compromis",
        "statut": "in_progress",
        "priorite": "urgent",
        "client": "Client Test Modifié",
        "sync_outlook": True,
    }
    with patch("management.views.update_outlook_event", return_value={"success": True, "event_id": "evt-1"}):
        response = _post_json(client, f"/api/update-activity/{activity.pk}/", update_payload)

    assert response.status_code == 200
    activity.refresh_from_db()
    assert activity.titre == "Relance compromis"
    assert activity.statut == "in_progress"
    assert activity.priorite == "urgent"
    assert activity.client == "Client Test Modifié"

    with patch("management.views.delete_outlook_event", return_value={"success": True}):
        response = _post_json(client, "/api/delete-activity/", {"activity_id": activity.pk})

    assert response.status_code == 200
    assert response.json()["deleted_count"] == 1
    assert not Activite.objects.filter(pk=activity.pk).exists()


@pytest.mark.django_db
def test_admin_project_create_update_delete_and_block_when_used(client, admin_user, type_activite):
    client.force_login(admin_user)

    response = _post_json(
        client,
        "/api/admin-projects/create/",
        {
            "reference": "adm-new",
            "name": "Projet administratif",
            "type": "juridique",
            "total_estimated": "125000.50",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    project = AdministrativeProject.objects.get(pk=data["project"]["id"])
    assert project.reference == "ADM-NEW"
    assert project.name == "Projet administratif"
    assert project.type == "juridique"

    response = _post_json(
        client,
        f"/api/admin-projects/{project.pk}/update/",
        {
            "reference": "ADM-UPD",
            "name": "Projet administratif modifié",
            "type": "client",
            "total_estimated": "130000",
        },
    )

    assert response.status_code == 200
    project.refresh_from_db()
    assert project.reference == "ADM-UPD"
    assert project.name == "Projet administratif modifié"
    assert project.type == "client"

    Activite.objects.create(
        id="project-blocked",
        titre="Activité liée",
        dossier=project,
        type=type_activite,
        date=timezone.now() + timedelta(days=2),
        date_type="date",
        statut="todo",
        priorite="normal",
        created_by=admin_user,
    )

    response = client.post(f"/api/admin-projects/{project.pk}/delete/")
    assert response.status_code == 409
    assert response.json()["success"] is False
    assert AdministrativeProject.objects.filter(pk=project.pk).exists()

    Activite.objects.filter(dossier=project).delete()
    response = client.post(f"/api/admin-projects/{project.pk}/delete/")
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert not AdministrativeProject.objects.filter(pk=project.pk).exists()


@pytest.mark.django_db
def test_admin_overview_and_projects_are_split(client, admin_user, dossier):
    client.force_login(admin_user)

    overview = client.get("/administratif/")
    projects = client.get("/administratif/projets/")

    assert overview.status_code == 200
    assert projects.status_code == 200
    assert b"admin-projects-data" not in overview.content
    assert b"admin-projects-data" in projects.content
    assert dossier.reference.encode() in projects.content


@pytest.mark.django_db
def test_activity_reminder_is_sent_once_and_creates_internal_notification(
    settings,
    responsable,
    dossier,
    type_activite,
):
    settings.EMAIL_HOST_USER = "fallback@example.com"
    activity = Activite.objects.create(
        id="1001",
        titre="Échéance J-7",
        dossier=dossier,
        type=type_activite,
        date=timezone.now() + timedelta(days=7),
        date_type="date",
        statut="todo",
        priorite="high",
        responsable=responsable,
        created_by=responsable,
    )

    with patch("management.tasks.EmailMessage.send", return_value=1) as send_mock:
        first = check_and_send_activite_reminders()
        second = check_and_send_activite_reminders()

    assert first["rappels_envoyes"] == 1
    assert second["rappels_envoyes"] == 0
    assert second["doublons_ignores"] == 1
    assert send_mock.call_count == 1
    assert HistoriqueRappelActivite.objects.filter(
        activite=activity,
        canal="email",
        jours_avant_echeance=7,
        statut="sent",
    ).count() == 1
    assert NotificationInterne.objects.filter(
        activite=activity,
        user=responsable,
        is_read=False,
    ).count() == 1


@pytest.mark.django_db
def test_finished_activity_does_not_generate_reminder(settings, responsable, dossier, type_activite):
    settings.EMAIL_HOST_USER = "fallback@example.com"
    Activite.objects.create(
        id="1002",
        titre="Activité terminée",
        dossier=dossier,
        type=type_activite,
        date=timezone.now() + timedelta(days=7),
        date_type="date",
        statut="done",
        priorite="normal",
        responsable=responsable,
        created_by=responsable,
    )

    with patch("management.tasks.EmailMessage.send", return_value=1) as send_mock:
        result = check_and_send_activite_reminders()

    assert result["activites_traitees"] == 0
    assert result["rappels_envoyes"] == 0
    assert send_mock.call_count == 0
    assert HistoriqueRappelActivite.objects.count() == 0
