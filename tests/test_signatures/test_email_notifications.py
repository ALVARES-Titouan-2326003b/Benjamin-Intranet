import pytest
from django.contrib.auth.models import Group, User
from django.core import mail
from django.urls import reverse

from signatures.forms import DocumentUploadForm
from signatures.models import SignatureRequest
from signatures.services.email import envoyer_demande_signature
from signatures.views import _can_user_sign_document, _get_signature_email_recipients


def test_formulaire_document_ne_demande_plus_le_signataire():
    form = DocumentUploadForm()

    assert "signataire_requis" not in form.fields


@pytest.mark.django_db
def test_envoyer_demande_signature_accepte_plusieurs_destinataires(
    settings,
    document_pdf_simple,
):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.DEFAULT_FROM_EMAIL = "intranet@example.com"
    mail.outbox = []

    destinataires = envoyer_demande_signature(
        [
            "admin@example.com",
            "ceo@example.com",
            "ADMIN@example.com",
            "",
        ],
        "https://example.test/signature",
        document_pdf_simple,
    )

    assert destinataires == ["admin@example.com", "ceo@example.com"]
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["admin@example.com", "ceo@example.com"]
    assert mail.outbox[0].subject == "[Signature requise] Document Test Simple"
    assert f"Document #{document_pdf_simple.pk}" not in mail.outbox[0].subject
    assert "attente d'approbation" in mail.outbox[0].body


@pytest.mark.django_db
def test_destinataires_signature_incluent_admin_et_superadmin(
    user_factory,
    pole_administratif_group,
):
    admin = user_factory(username="admin_signature", email="admin@example.com")
    admin.groups.add(pole_administratif_group)

    ceo_group = Group.objects.get_or_create(name="CEO")[0]
    ceo = user_factory(username="ceo_signature", email="ceo@example.com")
    ceo.groups.add(ceo_group)

    superadmin = User.objects.create_superuser(
        username="superadmin_signature",
        email="superadmin@example.com",
        password="testpass123",
    )

    destinataires = _get_signature_email_recipients(admin)

    assert set(destinataires) == {
        "admin@example.com",
        "ceo@example.com",
        "superadmin@example.com",
    }
    assert destinataires.count("admin@example.com") == 1
    assert superadmin.email in destinataires


@pytest.mark.django_db
def test_demande_signature_envoie_mail_admin_et_ceo(
    client,
    user_factory,
    document_pdf_simple,
    tampon_entreprise,
    pole_administratif_group,
    settings,
):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.DEFAULT_FROM_EMAIL = "intranet@example.com"
    mail.outbox = []

    technique_group = Group.objects.get_or_create(name="POLE_TECHNIQUE")[0]
    demandeur = user_factory(username="demandeur_signature", email="demandeur@example.com")
    demandeur.groups.add(technique_group)

    admin = user_factory(username="admin_signature", email="admin@example.com")
    admin.groups.add(pole_administratif_group)
    autre_admin = user_factory(username="autre_admin_signature", email="autre-admin@example.com")
    autre_admin.groups.add(pole_administratif_group)

    ceo_group = Group.objects.get_or_create(name="CEO")[0]
    ceo = user_factory(username="ceo_signature", email="ceo@example.com")
    ceo.groups.add(ceo_group)

    User.objects.create_superuser(
        username="superadmin_signature",
        email="superadmin@example.com",
        password="testpass123",
    )

    client.force_login(demandeur)

    response = client.post(
        reverse("signatures:placer_signature", args=[document_pdf_simple.pk]),
        {
            "pos_x_pct": "42",
            "pos_y_pct": "58",
            "admin_signer_id": str(autre_admin.pk),
            "signature_mode": "stamp_signature",
            "tampon_id": str(tampon_entreprise.pk),
        },
    )

    assert response.status_code == 302
    demande = SignatureRequest.objects.get(document=document_pdf_simple)
    assert demande.approver == autre_admin
    assert demande.size_scale_pct == 100.0
    assert demande.signature_mode == "stamp_signature"
    assert demande.tampon == tampon_entreprise
    assert len(mail.outbox) == 1
    assert set(mail.outbox[0].to) == {
        "autre-admin@example.com",
        "ceo@example.com",
        "superadmin@example.com",
    }

    assert _can_user_sign_document(admin, document_pdf_simple)
    assert _can_user_sign_document(ceo, document_pdf_simple)

    client.force_login(admin)
    response = client.get(reverse("signatures:signature_approval", args=[demande.token]))

    assert response.status_code == 403

    client.force_login(autre_admin)
    response = client.get(reverse("signatures:signature_approval", args=[demande.token]))

    assert response.status_code == 200

    client.force_login(ceo)
    response = client.get(reverse("signatures:signature_approval", args=[demande.token]))

    assert response.status_code == 200
