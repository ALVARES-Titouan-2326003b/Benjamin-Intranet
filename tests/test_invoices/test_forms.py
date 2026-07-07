import pytest

from invoices.forms import FactureForm, best_match, build_choices, normalize_label
from invoices.models import Client, InvoiceReminderSettings
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


def test_facture_form_service_uses_pole_choices():
    form = FactureForm()

    assert "client_input" not in form.fields
    assert form.fields["service"].choices == [
        ("", "-- Sélectionner un pôle --"),
        ("developpement", "Développement"),
        ("administratif", "Administratif"),
        ("technique", "Technique"),
        ("promotion", "Promotion"),
        ("investissement", "Investissement"),
        ("fonciere", "Foncière"),
        ("financier", "Financier"),
    ]


@pytest.mark.django_db
def test_facture_form_collaborateur_uses_active_users(user_factory):
    active = user_factory(username="active-user")
    inactive = user_factory(username="inactive-user", is_active=False)

    form = FactureForm()

    assert active in form.fields["collaborateur"].queryset
    assert inactive not in form.fields["collaborateur"].queryset


@pytest.mark.django_db
def test_facture_form_assigns_default_internal_client():
    project = TechnicalProject.objects.create(reference="DOS-001", name="Dossier Test")
    form = FactureForm(
        data={
            "fournisseur_input": "Fournisseur Test",
            "numero_facture": "FA-001",
            "societe": "Benjamin Immobilier",
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
