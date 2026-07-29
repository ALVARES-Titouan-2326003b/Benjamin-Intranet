import pytest
from django.contrib.auth.models import Group, User

from invoices.forms import FactureForm
from invoices.models import Societe
from technique.models import TechnicalProject


@pytest.fixture
def administratif_user(db):
    group, _ = Group.objects.get_or_create(name="POLE_ADMINISTRATIF")
    user = User.objects.create_user(username="gestion-societes")
    user.groups.add(group)
    return user


@pytest.fixture
def finance_user(db):
    group, _ = Group.objects.get_or_create(name="POLE_FINANCIER")
    user = User.objects.create_user(username="finance-societes")
    user.groups.add(group)
    return user


@pytest.fixture
def project(db):
    return TechnicalProject.objects.create(
        reference="SOC-ADMIN-001",
        name="Dossier lié à une société",
    )


@pytest.mark.django_db
def test_administratif_can_create_company(client, administratif_user):
    client.force_login(administratif_user)

    response = client.post(
        "/administratif/societes/",
        {"nom": "Nouvelle société administrative"},
    )

    assert response.status_code == 302
    assert response.url == "/administratif/societes/"
    company = Societe.objects.get(nom="Nouvelle société administrative")
    assert company.is_active is True
    assert company in FactureForm().fields["societe"].queryset


@pytest.mark.django_db
def test_finance_user_cannot_manage_administrative_company_referential(
    client, finance_user
):
    client.force_login(finance_user)

    response = client.get("/administratif/societes/")

    assert response.status_code == 302
    assert response.url == "/"


@pytest.mark.django_db
def test_unused_company_is_deleted(client, administratif_user):
    company = Societe.objects.create(nom="Société sans liaison")
    client.force_login(administratif_user)

    response = client.post(
        f"/administratif/societes/{company.pk}/supprimer/",
    )

    assert response.status_code == 302
    assert not Societe.objects.filter(pk=company.pk).exists()


@pytest.mark.django_db
def test_used_company_is_removed_from_selections_but_preserved(
    client, administratif_user, project
):
    company = Societe.objects.create(nom="Société déjà utilisée")
    project.societe = company
    project.save(update_fields=["societe"])
    client.force_login(administratif_user)

    response = client.post(
        f"/administratif/societes/{company.pk}/supprimer/",
    )

    assert response.status_code == 302
    company.refresh_from_db()
    assert company.is_active is False
    assert project.societe == company
    assert company not in FactureForm().fields["societe"].queryset


@pytest.mark.django_db
def test_administratif_can_restore_used_company(
    client, administratif_user, project
):
    company = Societe.objects.create(nom="Société à réactiver", is_active=False)
    project.societe = company
    project.save(update_fields=["societe"])
    client.force_login(administratif_user)

    response = client.post(
        f"/administratif/societes/{company.pk}/reactiver/",
    )

    assert response.status_code == 302
    company.refresh_from_db()
    assert company.is_active is True
    assert company in FactureForm().fields["societe"].queryset


@pytest.mark.django_db
def test_legacy_finance_company_url_redirects_to_administrative_referential(
    client, administratif_user
):
    client.force_login(administratif_user)

    response = client.get("/finance/societes/")

    assert response.status_code == 302
    assert response.url == "/administratif/societes/"
