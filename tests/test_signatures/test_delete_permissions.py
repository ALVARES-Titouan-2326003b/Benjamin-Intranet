import pytest
from django.contrib.auth.models import Group
from django.urls import reverse


@pytest.mark.django_db
def test_utilisateur_non_admin_ne_peut_pas_supprimer_document(
    client,
    user_factory,
    document_pdf_simple,
):
    technique_group = Group.objects.get_or_create(name="POLE_TECHNIQUE")[0]
    user = user_factory(username="signature_user", email="user@example.com")
    user.groups.add(technique_group)
    client.force_login(user)

    response = client.post(
        reverse("signatures:bulk_delete"),
        {"document_ids": [str(document_pdf_simple.pk)]},
    )

    assert response.status_code == 302
    assert type(document_pdf_simple).objects.filter(pk=document_pdf_simple.pk).exists()


@pytest.mark.django_db
def test_admin_peut_supprimer_document(
    client,
    user_factory,
    document_pdf_simple,
    pole_administratif_group,
):
    admin = user_factory(username="signature_admin", email="admin@example.com")
    admin.groups.add(pole_administratif_group)
    client.force_login(admin)

    response = client.post(
        reverse("signatures:bulk_delete"),
        {"document_ids": [str(document_pdf_simple.pk)]},
    )

    assert response.status_code == 302
    assert not type(document_pdf_simple).objects.filter(pk=document_pdf_simple.pk).exists()
