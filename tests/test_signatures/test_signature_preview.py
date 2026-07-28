import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_saved_signature_is_displayed_in_preview(client, signature_user_ceo):
    client.force_login(signature_user_ceo.user)

    response = client.get(reverse("signatures:ma_signature"))

    assert response.status_code == 200
    assert response.context["signature_user"] == signature_user_ceo
    assert signature_user_ceo.image.url in response.content.decode()
    assert "Signature actuelle" in response.content.decode()
    assert "Aucune signature n’est configurée" not in response.content.decode()
