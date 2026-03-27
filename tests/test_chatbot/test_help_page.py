import pytest
from django.contrib.auth.models import User
from django.urls import reverse


@pytest.mark.django_db
def test_chatbot_help_requires_login(client):
    response = client.get(reverse("chatbot:help"))

    assert response.status_code == 302
    assert "/login" in response.url


@pytest.mark.django_db
def test_chatbot_help_renders_expected_sections(client):
    user = User.objects.create_user(username="helpuser", password="pass123")
    client.force_login(user)

    response = client.get(reverse("chatbot:help"))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Périmètre du chatbot" in content
    assert "Exemples de questions utiles" in content
    assert "Limites et précautions" in content
    assert "Protection des données et bonnes pratiques" in content
    assert "Route <code>facture</code>" in content
    assert "Route <code>document</code>" in content
    assert "Route <code>juridique</code>" in content


@pytest.mark.django_db
def test_chatbot_history_contains_help_link(client):
    user = User.objects.create_user(username="historyuser", password="pass123")
    client.force_login(user)

    response = client.get(reverse("chatbot:history"))

    assert response.status_code == 200
    assert reverse("chatbot:help") in response.content.decode()
