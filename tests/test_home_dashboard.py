import pytest
from django.contrib.auth.models import Group, User


def _sidebar_navigation(response):
    html = response.content.decode()
    return html.split('<nav class="sidebar-nav">', 1)[1].split("</nav>", 1)[0]


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


@pytest.mark.django_db
def test_administrative_navigation_is_stable_and_has_no_duplicates(client):
    group, _ = Group.objects.get_or_create(name="POLE_ADMINISTRATIF")
    user = User.objects.create_user(
        username="navigation-admin",
        email="navigation-admin@example.com",
        is_staff=True,
    )
    user.groups.add(group)
    client.force_login(user)

    responses = [
        client.get("/administratif/"),
        client.get("/administratif/dossiers/"),
        client.get("/pole-technique/dossiers/"),
        client.get("/signatures/"),
    ]

    for response in responses:
        assert response.status_code == 200
        navigation = _sidebar_navigation(response)
        assert navigation.count("ADMINISTRATIF") == 1
        assert navigation.count("Dossiers techniques") == 1
        assert navigation.count("Signatures") == 1
        assert "TECHNIQUE" not in navigation
        assert "FINANCE" not in navigation

    technical_navigation = _sidebar_navigation(responses[2])
    assert 'Dossiers techniques\n      </a>' in technical_navigation
    assert 'class="nav-item active"' in technical_navigation


@pytest.mark.django_db
def test_multi_department_navigation_keeps_single_signature_entry(client):
    administrative_group, _ = Group.objects.get_or_create(name="POLE_ADMINISTRATIF")
    technical_group, _ = Group.objects.get_or_create(name="POLE_TECHNIQUE")
    user = User.objects.create_user(
        username="navigation-multi-poles",
        email="navigation-multi@example.com",
    )
    user.groups.add(administrative_group, technical_group)
    client.force_login(user)

    response = client.get("/administratif/")

    assert response.status_code == 200
    navigation = _sidebar_navigation(response)
    assert navigation.count("ADMINISTRATIF") == 1
    assert navigation.count("TECHNIQUE") == 1
    assert navigation.count("Signatures") == 1
    assert "Dossiers techniques" not in navigation
