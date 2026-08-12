from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("invoices", "0014_add_executive_assistant_group"),
    ]

    operations = [
        migrations.AlterField(
            model_name="facturehistorique",
            name="action",
            field=models.CharField(
                choices=[
                    ("status_change", "Changement de statut"),
                    ("reminder_sent", "Relance envoyée"),
                    ("reminder_skipped", "Relance ignorée"),
                    ("reminder_error", "Erreur de relance"),
                    ("user_action", "Action utilisateur"),
                    ("excel_sync_success", "Synchronisation Excel réussie"),
                    ("excel_sync_error", "Erreur de synchronisation Excel"),
                ],
                max_length=30,
            ),
        ),
    ]
