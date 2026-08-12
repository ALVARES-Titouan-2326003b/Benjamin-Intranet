import json
from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group, User
from django.urls import reverse

from chatbot.models import ChatbotQuery
from chatbot.services.case_context import build_case_context, resolve_case
from chatbot.views import (
    _build_rag_context,
    _handle_case_query,
    _handle_invoice_query,
    _route_fallback,
)
from invoices.models import ActeurExterne, Client, Facture, Fournisseur
from technique.models import (
    DocumentTechnique,
    ProjectExpense,
    TechnicalProject,
    TechnicalProjectAction,
    TechnicalProjectKeyDate,
)


def test_fallback_router_distinguishes_case_and_invoice_references():
    assert _route_fallback("Résumé du dossier CASE-001") == "case"
    assert _route_fallback("Montre la facture FAC-2026-001") == "invoice"


@pytest.mark.django_db
def test_chatbot_query_requires_authentication(client):
    response = client.post(
        reverse("chatbot:query"),
        data=json.dumps({"message": "bonjour"}),
        content_type="application/json",
    )
    assert response.status_code == 302


@pytest.mark.django_db
def test_chatbot_query_persists_each_exchange(client, monkeypatch):
    user = User.objects.create_user(username="bob", password="pass123")
    client.force_login(user)
    monkeypatch.setattr("chatbot.views._route_message", lambda _message: "legal")
    monkeypatch.setattr("chatbot.views._handle_legal_query", lambda _message: "Réponse test")

    for message in ["Question 1", "Question 2"]:
        response = client.post(
            reverse("chatbot:query"),
            data=json.dumps({"message": message}),
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    assert ChatbotQuery.objects.filter(user=user).count() == 2


@pytest.mark.django_db
def test_chatbot_history_is_private_and_filterable(client):
    owner = User.objects.create_user(username="charlie", password="pass123")
    other = User.objects.create_user(username="other", password="pass123")
    ChatbotQuery.objects.create(
        user=owner,
        message="Question juridique DPE",
        response="Réponse",
        query_type="legal",
    )
    ChatbotQuery.objects.create(
        user=owner,
        message="Question facture",
        response="Réponse",
        query_type="invoice",
    )
    ChatbotQuery.objects.create(
        user=other,
        message="Question juridique privée",
        response="Réponse",
        query_type="legal",
    )

    client.force_login(owner)
    response = client.get(
        reverse("chatbot:history"),
        {"type": "legal", "q": "DPE"},
    )

    assert response.status_code == 200
    rows = list(response.context["queries"])
    assert len(rows) == 1
    assert rows[0].user == owner
    assert rows[0].message == "Question juridique DPE"


@pytest.mark.django_db
def test_invoice_query_searches_supplier_foreign_key_by_name():
    user = User.objects.create_user(username="finance", password="pass123")
    supplier_actor = ActeurExterne.objects.create(id="CHATBOT-SUPPLIER")
    supplier = Fournisseur.objects.create(id=supplier_actor, nom="Entreprise Martin")
    client_actor = ActeurExterne.objects.create(id="CHATBOT-CLIENT")
    invoice_client = Client.objects.create(id=client_actor)
    Facture.objects.create(
        id="FAC-CHATBOT-0001",
        fournisseur=supplier,
        client=invoice_client,
        montant=1250,
        statut="received",
        created_by=user,
    )

    response = _handle_invoice_query("factures fournisseur Martin", user)

    assert "FAC-CHATBOT-0001" in response
    assert "1250" in response


@pytest.mark.django_db
def test_invoice_query_uses_current_status_values():
    user = User.objects.create_user(username="accounting", password="pass123")
    supplier_actor = ActeurExterne.objects.create(id="CHATBOT-PENDING-SUPPLIER")
    supplier = Fournisseur.objects.create(id=supplier_actor, nom="Entreprise en attente")
    client_actor = ActeurExterne.objects.create(id="CHATBOT-PENDING-CLIENT")
    invoice_client = Client.objects.create(id=client_actor)
    Facture.objects.create(
        id="FAC-CHATBOT-PENDING",
        fournisseur=supplier,
        client=invoice_client,
        montant=800,
        statut="pending",
        created_by=user,
    )

    response = _handle_invoice_query("factures en attente", user)

    assert "FAC-CHATBOT-PENDING" in response
    assert "En attente" in response


@pytest.mark.django_db
def test_invoice_query_does_not_expose_another_users_invoice():
    owner = User.objects.create_user(username="invoice-owner", password="pass123")
    outsider = User.objects.create_user(username="invoice-outsider", password="pass123")
    supplier_actor = ActeurExterne.objects.create(id="PRIVATE-SUPPLIER")
    supplier = Fournisseur.objects.create(id=supplier_actor, nom="Fournisseur privé")
    client_actor = ActeurExterne.objects.create(id="PRIVATE-CLIENT")
    invoice_client = Client.objects.create(id=client_actor)
    Facture.objects.create(
        id="FAC-PRIVATE-0001",
        fournisseur=supplier,
        client=invoice_client,
        montant=999,
        statut="received",
        created_by=owner,
    )

    response = _handle_invoice_query("facture FAC-PRIVATE-0001", outsider)

    assert "999" not in response
    assert "Fournisseur privé" not in response
    assert "Aucune facture accessible" in response


@pytest.mark.django_db
def test_rag_context_searches_current_document_project_fields(societe):
    user = User.objects.create_user(username="technical-rag", password="pass123")
    user.groups.add(Group.objects.get_or_create(name="POLE_TECHNIQUE")[0])
    project = TechnicalProject.objects.create(
        reference="RAG-001",
        name="Résidence des Acacias",
        societe=societe,
    )
    DocumentTechnique.objects.create(
        project=project,
        titre="Promesse de vente",
        fichier="documents_tech/promesse.pdf",
        resume="Le délai de réitération est fixé à trois mois.",
    )

    context = _build_rag_context("Que prévoit le dossier Acacias ?", user)

    assert "Promesse de vente" in context
    assert "RAG-001 - Résidence des Acacias" in context


@pytest.mark.django_db
def test_rag_context_does_not_expose_documents_to_unauthorized_user(societe):
    user = User.objects.create_user(username="no-document-access", password="pass123")
    project = TechnicalProject.objects.create(
        reference="RAG-SECRET",
        name="Dossier confidentiel",
        societe=societe,
    )
    DocumentTechnique.objects.create(
        project=project,
        titre="Promesse confidentielle",
        fichier="documents_tech/secret.pdf",
        resume="Information strictement confidentielle.",
    )

    assert _build_rag_context("Promesse confidentielle", user) == ""


@pytest.mark.django_db
def test_case_resolution_only_uses_projects_visible_to_user(societe):
    project = TechnicalProject.objects.create(
        reference="CASE-SECRET",
        name="Affaire secrète",
        societe=societe,
    )
    unauthorized = User.objects.create_user(username="case-outsider", password="pass123")
    authorized = User.objects.create_user(username="case-tech", password="pass123")
    authorized.groups.add(Group.objects.get_or_create(name="POLE_TECHNIQUE")[0])

    assert resolve_case("Résumé du dossier CASE-SECRET", unauthorized).project is None
    assert resolve_case("Résumé du dossier CASE-SECRET", authorized).project == project


@pytest.mark.django_db
def test_executive_assistant_has_global_read_access_without_invoice_edit_rights(societe):
    owner = User.objects.create_user(username="invoice-owner-direction")
    assistant = User.objects.create_user(username="executive-assistant")
    assistant.groups.add(Group.objects.get_or_create(name="ASSISTANTE_DIRECTION")[0])
    project = TechnicalProject.objects.create(
        reference="CASE-DIRECTION",
        name="Dossier Direction",
        societe=societe,
    )
    supplier_actor = ActeurExterne.objects.create(id="DIRECTION-SUPPLIER")
    supplier = Fournisseur.objects.create(id=supplier_actor, nom="Fournisseur Direction")
    client_actor = ActeurExterne.objects.create(id="DIRECTION-CLIENT")
    invoice_client = Client.objects.create(id=client_actor)
    invoice = Facture.objects.create(
        id="FAC-DIRECTION-001",
        fournisseur=supplier,
        client=invoice_client,
        dossier=project,
        montant=4200,
        created_by=owner,
    )

    assert resolve_case("Résumé CASE-DIRECTION", assistant).project == project
    assert "FAC-DIRECTION-001" in build_case_context(project, assistant).prompt

    from user_access.user_test_functions import can_edit_facture

    assert can_edit_facture(assistant, invoice) is False


@pytest.mark.django_db
def test_case_query_combines_finances_dates_actions_documents_and_sources(
    societe,
    settings,
):
    settings.GROQ_API_KEY = ""
    user = User.objects.create_user(username="case-owner", password="pass123")
    user.groups.add(Group.objects.get_or_create(name="POLE_TECHNIQUE")[0])
    project = TechnicalProject.objects.create(
        reference="CASE-001",
        name="Résidence Horizon",
        societe=societe,
        total_estimated=Decimal("10000.00"),
    )
    supplier_actor = ActeurExterne.objects.create(id="CASE-SUPPLIER")
    supplier = Fournisseur.objects.create(id=supplier_actor, nom="Entreprise Horizon")
    client_actor = ActeurExterne.objects.create(id="CASE-CLIENT")
    invoice_client = Client.objects.create(id=client_actor)
    invoice = Facture.objects.create(
        id="FAC-CASE-001",
        fournisseur=supplier,
        client=invoice_client,
        dossier=project,
        montant=2500,
        statut="pending",
        created_by=user,
    )
    ProjectExpense.objects.create(
        project=project,
        facture=invoice,
        label="Études",
        amount=Decimal("2500.00"),
        is_paid=True,
    )
    TechnicalProjectAction.objects.create(
        project=project,
        title="Déposer le permis",
        assigned_to=user,
        due_date=date(2026, 9, 10),
    )
    TechnicalProjectKeyDate.objects.create(
        project=project,
        label="Signature de l'acte",
        date=date(2026, 10, 1),
        status="planned",
    )
    DocumentTechnique.objects.create(
        project=project,
        titre="Promesse Horizon",
        fichier="documents_tech/horizon.pdf",
        resume="La réitération doit intervenir avant octobre.",
    )

    answer = _handle_case_query("Résume le dossier CASE-001", user)

    assert "CASE-001 — Résidence Horizon" in answer
    assert "10 000,00 €" in answer
    assert "2 500,00 €" in answer
    assert "Factures visibles : 1" in answer
    assert "Dates clés : 1" in answer
    assert "actions ouvertes : 1" in answer
    assert "documents accessibles : 1" in answer
    assert reverse("technique:dossier_detail", args=[project.pk]) in answer
    assert reverse("invoices:detail", args=[invoice.pk]) in answer


@pytest.mark.django_db
def test_case_context_includes_administrative_activity_and_fields(societe):
    from management.models import (
        Activite,
        ChampPersonnaliseDossier,
        ValeurChampPersonnaliseDossier,
    )

    user = User.objects.create_user(username="admin-context")
    user.groups.add(Group.objects.get_or_create(name="POLE_ADMINISTRATIF")[0])
    project = TechnicalProject.objects.create(
        reference="CASE-ADMIN-001",
        name="Dossier administratif global",
        societe=societe,
    )
    Activite.objects.create(
        id="CHATBOT-ADMIN-ACTIVITY",
        dossier=project,
        titre="Relire la promesse",
        responsable=user,
    )
    field = ChampPersonnaliseDossier.objects.create(label="Notaire référent")
    ValeurChampPersonnaliseDossier.objects.create(
        dossier=project,
        field=field,
        value="Maître Martin",
    )

    context = build_case_context(project, user)

    assert "ACTIVITÉS ADMINISTRATIVES OUVERTES" in context.prompt
    assert "Relire la promesse" in context.prompt
    assert "Notaire référent : Maître Martin" in context.prompt
    assert reverse("admin_dossier_detail", args=[project.pk]) in context.fallback_answer


@pytest.mark.django_db
def test_chatbot_routes_case_query_and_saves_it(client, monkeypatch, societe, settings):
    settings.GROQ_API_KEY = ""
    user = User.objects.create_user(username="case-chat", password="pass123")
    user.groups.add(Group.objects.get_or_create(name="POLE_TECHNIQUE")[0])
    TechnicalProject.objects.create(
        reference="CASE-CHAT-001",
        name="Dossier Chat",
        societe=societe,
    )
    client.force_login(user)
    monkeypatch.setattr("chatbot.views._route_message", lambda _message: "case")

    response = client.post(
        reverse("chatbot:query"),
        data=json.dumps({"message": "Résumé du dossier CASE-CHAT-001"}),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["query_type"] == "case"
    assert ChatbotQuery.objects.get(user=user).query_type == "case"
