from django.db import migrations, models


def migrate_invoice_statuses(apps, schema_editor):
    Facture = apps.get_model("invoices", "Facture")
    Facture.objects.exclude(statut="received").update(statut="pending")


def restore_legacy_pending_status(apps, schema_editor):
    Facture = apps.get_model("invoices", "Facture")
    Facture.objects.filter(statut="pending").update(statut="ongoing")


class Migration(migrations.Migration):
    dependencies = [
        ("invoices", "0010_remove_invoice_reminder_system"),
    ]

    operations = [
        migrations.RunPython(
            migrate_invoice_statuses,
            restore_legacy_pending_status,
        ),
        migrations.AlterField(
            model_name="facture",
            name="statut",
            field=models.TextField(
                choices=[
                    ("received", "Reçue"),
                    ("pending", "En attente"),
                ],
                default="received",
            ),
        ),
        migrations.AddConstraint(
            model_name="facture",
            constraint=models.CheckConstraint(
                condition=models.Q(statut__in=["received", "pending"]),
                name="facture_valid_status",
            ),
        ),
    ]
