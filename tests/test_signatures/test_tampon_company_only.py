import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError

from invoices.models import Societe
from signatures.forms import TamponForm
from signatures.models import Tampon


@pytest.mark.django_db
def test_tampon_uses_company_without_name():
    field_names = {field.name for field in Tampon._meta.fields}
    assert "nom" not in field_names
    assert list(TamponForm().fields) == ["societe", "image", "is_active"]
    assert Tampon._meta.get_field("societe").remote_field.model._meta.label == "invoices.Societe"


@pytest.mark.django_db
def test_a_company_can_only_have_one_stamp():
    company = Societe.objects.create(nom="Société unique")
    Tampon.objects.create(
        societe=company,
        image=SimpleUploadedFile("tampon-1.png", b"image"),
    )

    with pytest.raises(IntegrityError):
        Tampon.objects.create(
            societe=company,
            image=SimpleUploadedFile("tampon-2.png", b"image"),
        )


@pytest.mark.django_db
def test_stamp_form_only_offers_companies_without_stamp():
    occupied_company = Societe.objects.create(nom="Société équipée")
    available_company = Societe.objects.create(nom="Société disponible")
    stamp = Tampon.objects.create(
        societe=occupied_company,
        image=SimpleUploadedFile("tampon.png", b"image"),
    )

    creation_form = TamponForm()
    assert available_company in creation_form.fields["societe"].queryset
    assert occupied_company not in creation_form.fields["societe"].queryset

    update_form = TamponForm(instance=stamp)
    assert occupied_company in update_form.fields["societe"].queryset
