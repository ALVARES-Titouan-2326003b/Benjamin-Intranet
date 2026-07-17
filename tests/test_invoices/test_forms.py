import pytest
from django.utils import timezone

from invoices.forms import FactureForm, best_match, build_choices, normalize_label
from invoices.models import Client, InvoiceReminderSettings, Societe
from technique.models import TechnicalProject


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Café Français", "cafe francais"),
        ("Hello_World", "hello world"),
        ("", ""),
        (None, None),
    ],
)
def test_normalize_label(value, expected):
    assert normalize_label(value) == expected


def test_choice_helpers():
    labels = ["Technique", "Comptabilité et Finance"]
    assert best_match("comptabilite_et finance", labels) == "Comptabilité et Finance"
    assert build_choices(labels) == [(label, label) for label in labels]


def test_facture_form_keeps_service_assignment_outside_user_input():
    form = FactureForm()

    assert "client_input" not in form.fields
    assert "service" not in form.fields


@pytest.mark.django_db
def test_facture_form_keeps_requester_assignment_outside_user_input():
    form = FactureForm()

    assert "collaborateur" not in form.fields


@pytest.mark.django_db
def test_facture_form_excludes_archived_projects():
    active = TechnicalProject.objects.create(reference="DOS-ACTIF", name="Dossier actif")
    archived = TechnicalProject.objects.create(
        reference="DOS-ARCHIVE",
        name="Dossier archivé",
        archived_at=timezone.now(),
    )

    queryset = FactureForm().fields["dossier"].queryset

    assert active in queryset
    assert archived not in queryset


@pytest.mark.django_db
def test_facture_form_assigns_default_internal_client():
    project = TechnicalProject.objects.create(reference="DOS-001", name="Dossier Test")
    company = Societe.objects.create(nom="Benjamin Immobilier")
    form = FactureForm(
        data={
            "fournisseur_input": "Fournisseur Test",
            "numero_facture": "FA-001",
            "societe": company.pk,
            "affaire": "Dossier Test",
            "dossier": project.pk,
            "montant": "120.50",
            "statut": "ongoing",
            "service": "financier",
            "priorite": "normal",
            "titre": "Facture test",
        }
    )

    assert form.is_valid(), form.errors
    facture = form.save()

    assert facture.client_id == "DIVERS"
    assert Client.objects.filter(pk="DIVERS").exists()


@pytest.mark.django_db
def test_invoice_reminder_settings_is_a_singleton(user_factory):
    first = InvoiceReminderSettings.objects.create(sender=user_factory(username="finance-1"))
    second = InvoiceReminderSettings(sender=user_factory(username="finance-2"))
    second.save()

    assert first.pk == 1
    assert second.pk == 1
    assert InvoiceReminderSettings.objects.count() == 1
    assert InvoiceReminderSettings.objects.get().sender.username == "finance-2"
