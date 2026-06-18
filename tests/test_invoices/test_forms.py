import pytest

from invoices.forms import best_match, build_choices, normalize_label
from invoices.models import InvoiceReminderSettings


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


@pytest.mark.django_db
def test_invoice_reminder_settings_is_a_singleton(user_factory):
    first = InvoiceReminderSettings.objects.create(sender=user_factory(username="finance-1"))
    second = InvoiceReminderSettings(sender=user_factory(username="finance-2"))
    second.save()

    assert first.pk == 1
    assert second.pk == 1
    assert InvoiceReminderSettings.objects.count() == 1
    assert InvoiceReminderSettings.objects.get().sender.username == "finance-2"
