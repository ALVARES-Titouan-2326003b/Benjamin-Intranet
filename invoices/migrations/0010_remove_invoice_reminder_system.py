from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("invoices", "0009_remove_unused_legacy_models"),
    ]

    operations = [
        migrations.DeleteModel(name="InvoiceReminderSettings"),
        migrations.DeleteModel(name="RelanceFournisseur"),
    ]
