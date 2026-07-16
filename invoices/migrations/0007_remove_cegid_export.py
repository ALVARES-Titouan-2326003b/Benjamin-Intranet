from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("invoices", "0006_optional_invoice_project"),
    ]

    operations = [
        migrations.DeleteModel(
            name="ExportCegidRun",
        ),
    ]
