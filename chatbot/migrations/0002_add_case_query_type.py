from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("chatbot", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="chatbotquery",
            name="query_type",
            field=models.CharField(
                choices=[
                    ("case", "Dossier / affaire"),
                    ("invoice", "Facture"),
                    ("document", "Document interne"),
                    ("legal", "Juridique"),
                    ("legal_fallback", "Juridique fallback"),
                    ("unknown", "Inconnu"),
                ],
                default="unknown",
                max_length=20,
                verbose_name="Type de requête",
            ),
        ),
    ]
