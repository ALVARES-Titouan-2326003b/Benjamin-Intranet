import pytest
from django.contrib.auth.models import Group, User


@pytest.mark.django_db
def test_administratif_user_can_access_invoice_submission_from_dashboard(client):
    group, _ = Group.objects.get_or_create(name="POLE_ADMINISTRATIF")
    user = User.objects.create_user(username="admin-pole", email="admin-pole@example.com")
    user.groups.add(group)
    client.force_login(user)

    response = client.get("/")

    assert response.status_code == 200
    assert b"Factures" in response.content
    assert b"/finance/" in response.content
