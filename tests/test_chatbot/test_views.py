import json

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from chatbot.models import ChatbotQuery


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
