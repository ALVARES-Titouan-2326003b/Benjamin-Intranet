import pytest
from django.utils import timezone

from invoices.forms import FactureForm, PieceJointeForm, best_match, build_choices, normalize_label
from invoices.models import Client, Facture, Societe
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


def test_invoice_statuses_are_limited_to_received_and_pending():
    assert Facture.STATUS == [
        ("received", "Reçue"),
        ("pending", "En attente"),
    ]
    assert Facture().statut == "received"
    assert list(FactureForm().fields["statut"].choices) == Facture.STATUS


def test_invoice_attachment_can_be_required_on_creation():
    form = PieceJointeForm(data={}, files={}, required=True)

    assert not form.is_valid()
    assert "Ce champ est obligatoire" in form.errors["fichier"][0]


def test_invoice_attachment_stays_optional_on_update():
    form = PieceJointeForm(data={}, files={}, required=False)

    assert form.is_valid()


@pytest.mark.django_db
def test_facture_form_keeps_requester_assignment_outside_user_input():
    form = FactureForm()

    assert "collaborateur" not in form.fields


@pytest.mark.django_db
def test_facture_form_excludes_archived_projects(societe):
    active = TechnicalProject.objects.create(
        reference="DOS-ACTIF", name="Dossier actif", societe=societe
    )
    archived = TechnicalProject.objects.create(
        reference="DOS-ARCHIVE",
        name="Dossier archivé",
        societe=societe,
        archived_at=timezone.now(),
    )

    queryset = FactureForm().fields["dossier"].queryset

    assert active in queryset
    assert archived not in queryset


@pytest.mark.django_db
def test_facture_form_assigns_default_internal_client(societe):
    project = TechnicalProject.objects.create(
        reference="DOS-001", name="Dossier Test", societe=societe
    )
    company = societe
    form = FactureForm(
        data={
            "fournisseur_input": "Fournisseur Test",
            "numero_facture": "FA-001",
            "societe": company.pk,
            "affaire": "Dossier Test",
            "dossier": project.pk,
            "montant": "120.50",
            "statut": "received",
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
def test_facture_form_rejects_project_from_another_company(societe):
    project = TechnicalProject.objects.create(
        reference="DOS-SOCIETE",
        name="Dossier société",
        societe=societe,
    )
    other_company = Societe.objects.create(nom="Société erronée")
    form = FactureForm(
        data={
            "fournisseur_input": "Fournisseur Test",
            "numero_facture": "FA-SOCIETE",
            "societe": other_company.pk,
            "dossier": project.pk,
            "montant": "120.50",
            "statut": "received",
            "priorite": "normal",
        }
    )

    assert not form.is_valid()
    assert "Ce dossier n’est pas rattaché à la société sélectionnée." in form.errors["dossier"]


@pytest.mark.django_db
def test_facture_form_rejects_project_without_selected_company(societe):
    project = TechnicalProject.objects.create(
        reference="DOS-SANS-SOCIETE",
        name="Dossier sans sélection préalable",
        societe=societe,
    )
    form = FactureForm(
        data={
            "fournisseur_input": "Fournisseur Test",
            "numero_facture": "FA-SANS-SOCIETE",
            "societe": "",
            "dossier": project.pk,
            "montant": "120.50",
            "statut": "received",
            "priorite": "normal",
        }
    )

    assert not form.is_valid()
    assert "Sélectionnez une société avant de choisir un dossier." in form.errors["societe"]


@pytest.mark.django_db
def test_invoice_project_options_expose_their_company_for_dynamic_filtering(societe):
    project = TechnicalProject.objects.create(
        reference="DOS-FILTRE",
        name="Dossier filtrable",
        societe=societe,
    )

    html = str(FactureForm()["dossier"])

    assert f'value="{project.pk}"' in html
    assert f'data-societe-id="{societe.pk}"' in html
