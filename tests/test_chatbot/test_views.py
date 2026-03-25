import json

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from chatbot.models import ChatSession, ChatbotQuery


@pytest.mark.django_db
def test_chatbot_query_requires_csrf():
    user = User.objects.create_user(username="alice", password="pass123")
    client = Client(enforce_csrf_checks=True)
    client.login(username="alice", password="pass123")

    resp = client.post(
        reverse("chatbot:query"),
        data=json.dumps({"message": "bonjour"}),
        content_type="application/json",
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_chatbot_query_with_session_reuse(client, monkeypatch):
    user = User.objects.create_user(username="bob", password="pass123")
    client.login(username="bob", password="pass123")

    monkeypatch.setattr("chatbot.views._route_message", lambda _message: "legal")
    monkeypatch.setattr("chatbot.views._handle_legal_query", lambda _message, _history: ("Reponse test", []))

    first = client.post(
        reverse("chatbot:query"),
        data=json.dumps({"message": "Question 1"}),
        content_type="application/json",
    )
    assert first.status_code == 200
    payload_1 = first.json()
    assert payload_1["success"] is True
    assert payload_1["session_id"]

    second = client.post(
        reverse("chatbot:query"),
        data=json.dumps({"message": "Question 2", "session_id": payload_1["session_id"]}),
        content_type="application/json",
    )
    assert second.status_code == 200
    payload_2 = second.json()
    assert payload_2["session_id"] == payload_1["session_id"]

    session = ChatSession.objects.get(id=payload_1["session_id"])
    assert session.queries.count() == 2


@pytest.mark.django_db
def test_chatbot_history_is_paginated(client):
    user = User.objects.create_user(username="charlie", password="pass123")
    client.login(username="charlie", password="pass123")

    for idx in range(25):
        ChatbotQuery.objects.create(
            user=user,
            message=f"Question {idx}",
            response="Reponse",
            query_type="legal",
        )

    response = client.get(reverse("chatbot:history"))
    assert response.status_code == 200
    assert len(response.context["queries"]) == 20
    assert response.context["total_results"] == 25
    assert response.context["page_obj"].paginator.num_pages == 2


@pytest.mark.django_db
def test_chatbot_history_delete_only_owner(client):
    owner = User.objects.create_user(username="owner", password="pass123")
    other = User.objects.create_user(username="other", password="pass123")

    own_row = ChatbotQuery.objects.create(
        user=owner,
        message="Q1",
        response="R1",
        query_type="legal",
    )
    other_row = ChatbotQuery.objects.create(
        user=other,
        message="Q2",
        response="R2",
        query_type="legal",
    )

    client.login(username="owner", password="pass123")
    resp = client.post(reverse("chatbot:history_delete", args=[own_row.id]))
    assert resp.status_code == 302
    assert not ChatbotQuery.objects.filter(id=own_row.id).exists()
    assert ChatbotQuery.objects.filter(id=other_row.id).exists()
