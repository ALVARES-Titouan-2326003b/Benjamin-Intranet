import pytest

from signatures.forms import TamponForm
from signatures.models import Tampon


@pytest.mark.django_db
def test_tampon_uses_company_without_name():
    field_names = {field.name for field in Tampon._meta.fields}
    assert "nom" not in field_names
    assert list(TamponForm().fields) == ["societe", "image", "is_active"]
