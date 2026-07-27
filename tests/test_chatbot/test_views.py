import json

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from chatbot.models import ChatbotQuery
from chatbot.views import _build_rag_context, _handle_invoice_query
from invoices.models import ActeurExterne, Client, Facture, Fournisseur
from technique.models import DocumentTechnique, TechnicalProject


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
    )

    response = _handle_invoice_query("factures fournisseur Martin", user)

    assert "FAC-CHATBOT-0001" in response
    assert "1250" in response


@pytest.mark.django_db
def test_invoice_query_uses_current_status_values():
    user = User.objects.create_user(username="accounting", password="pass123")
    supplier_actor = ActeurExterne.objects.create(id="CHATBOT-PAID-SUPPLIER")
    supplier = Fournisseur.objects.create(id=supplier_actor, nom="Entreprise Payée")
    client_actor = ActeurExterne.objects.create(id="CHATBOT-PAID-CLIENT")
    invoice_client = Client.objects.create(id=client_actor)
    Facture.objects.create(
        id="FAC-CHATBOT-PAID",
        fournisseur=supplier,
        client=invoice_client,
        montant=800,
        statut="paid",
    )

    response = _handle_invoice_query("factures payées", user)

    assert "FAC-CHATBOT-PAID" in response
    assert "Payée" in response


@pytest.mark.django_db
def test_rag_context_searches_current_document_project_fields():
    project = TechnicalProject.objects.create(
        reference="RAG-001",
        name="Résidence des Acacias",
    )
    DocumentTechnique.objects.create(
        project=project,
        titre="Promesse de vente",
        fichier="documents_tech/promesse.pdf",
        resume="Le délai de réitération est fixé à trois mois.",
    )

    context = _build_rag_context("Que prévoit le dossier Acacias ?")

    assert "Promesse de vente" in context
    assert "RAG-001 - Résidence des Acacias" in context
