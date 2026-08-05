import pytest
from django.contrib.auth.models import Group
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from signatures.forms import SignatureUserForm
from signatures.models import SignatureRequest, SignatureUser


def test_formulaire_signature_demande_le_nom_du_signataire():
    form = SignatureUserForm()

    assert list(form.fields) == ["name", "image", "is_active"]
    assert form.fields["name"].label == "Nom du signataire"


@pytest.mark.django_db
def test_un_gestionnaire_peut_enregistrer_plusieurs_signatures_nommees(
    client,
    signature_user_ceo,
):
    client.force_login(signature_user_ceo.user)
    signature_user_ceo.image.open("rb")
    signature_bytes = signature_user_ceo.image.read()

    response = client.post(
        reverse("signatures:ma_signature"),
        {
            "name": "Rudy Martin",
            "is_active": "on",
            "image": SimpleUploadedFile(
                "rudy.png",
                signature_bytes,
                content_type="image/png",
            ),
        },
    )

    assert response.status_code == 302
    assert SignatureUser.objects.filter(user=signature_user_ceo.user).count() == 2
    created = SignatureUser.objects.get(name="Rudy Martin")
    assert created.is_active is True

    response = client.get(reverse("signatures:ma_signature"))
    content = response.content.decode()
    assert "Bibliothèque des signatures" in content
    assert "Rudy Martin" in content
    assert created.image.url in content


@pytest.mark.django_db
def test_la_signature_choisie_est_apposee_independamment_du_compte_validateur(
    client,
    document_pdf_simple,
    signature_user_ceo,
    user_factory,
    settings,
):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    technique = Group.objects.get_or_create(name="POLE_TECHNIQUE")[0]
    administratif = Group.objects.get_or_create(name="POLE_ADMINISTRATIF")[0]
    requester = user_factory(username="demandeur_bibliotheque", email="demandeur@example.com")
    requester.groups.add(technique)
    approver = user_factory(username="approbateur_bibliotheque", email="approbateur@example.com")
    approver.groups.add(administratif)

    selected_signature = SignatureUser.objects.create(
        user=requester,
        name="Mégane Durand",
    )
    signature_user_ceo.image.open("rb")
    selected_signature.image.save(
        "megane.png",
        ContentFile(signature_user_ceo.image.read()),
        save=True,
    )

    client.force_login(requester)
    response = client.post(
        reverse("signatures:placer_signature", args=[document_pdf_simple.pk]),
        {
            "pos_x_pct": "20",
            "pos_y_pct": "10",
            "page_number": "1",
            "signature_mode": "signature",
            "signature_profile_id": str(selected_signature.pk),
            "admin_signer_id": str(approver.pk),
            "signature_mention_choice": "",
        },
    )

    assert response.status_code == 302
    request = SignatureRequest.objects.get(document=document_pdf_simple)
    assert request.signature_profile == selected_signature

    client.force_login(signature_user_ceo.user)
    response = client.post(
        reverse("signatures:signature_approval", args=[request.token]),
        {"action": "approve", "commentaire": "Validé"},
    )

    assert response.status_code == 302
    document_pdf_simple.refresh_from_db()
    assert document_pdf_simple.fichier_signe
    assert document_pdf_simple.signature_profile == selected_signature


@pytest.mark.django_db
def test_le_placement_ne_propose_que_les_signatures_actives(
    client,
    document_pdf_simple,
    signature_user_ceo,
):
    inactive = SignatureUser.objects.create(
        user=signature_user_ceo.user,
        name="Ancienne signature",
        image=signature_user_ceo.image.name,
        is_active=False,
    )
    client.force_login(signature_user_ceo.user)

    response = client.get(
        reverse("signatures:placer_signature", args=[document_pdf_simple.pk])
    )

    assert response.status_code == 200
    assert signature_user_ceo in response.context["available_signatures"]
    assert inactive not in response.context["available_signatures"]
    assert b'name="signature_profile_id"' in response.content
