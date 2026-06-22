import pytest
from django.contrib.auth.models import Group, User
from django.core import mail
from django.urls import reverse

from signatures.models import SignatureRequest
from signatures.services.email import envoyer_demande_signature
from signatures.views import _get_signature_email_recipients


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
def test_demande_signature_envoie_mail_admin_et_superadmin(
    client,
    user_factory,
    document_pdf_simple,
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

    User.objects.create_superuser(
        username="superadmin_signature",
        email="superadmin@example.com",
        password="testpass123",
    )

    document_pdf_simple.signataire_requis = "RH"
    document_pdf_simple.save()
    client.force_login(demandeur)

    response = client.post(
        reverse("signatures:placer_signature", args=[document_pdf_simple.pk]),
        {"pos_x_pct": "42", "pos_y_pct": "58"},
    )

    assert response.status_code == 302
    demande = SignatureRequest.objects.get(document=document_pdf_simple)
    assert demande.approver == admin
    assert len(mail.outbox) == 1
    assert set(mail.outbox[0].to) == {"admin@example.com", "superadmin@example.com"}
