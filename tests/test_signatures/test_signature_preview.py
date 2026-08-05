import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_saved_signature_is_displayed_in_preview(client, signature_user_ceo):
    client.force_login(signature_user_ceo.user)

    response = client.get(reverse("signatures:ma_signature"))

    assert response.status_code == 200
    assert signature_user_ceo in response.context["signatures_library"]
    assert signature_user_ceo.image.url in response.content.decode()
    assert "Bibliothèque des signatures" in response.content.decode()
    assert "Aucune signature enregistrée" not in response.content.decode()
