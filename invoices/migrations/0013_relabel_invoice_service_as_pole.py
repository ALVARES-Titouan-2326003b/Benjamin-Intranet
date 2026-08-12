from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("invoices", "0012_normalize_legacy_reminder_email"),
    ]

    operations = [
        migrations.AlterField(
            model_name="facture",
            name="service",
            field=models.CharField(
                blank=True,
                choices=[
                    ("developpement", "Développement"),
                    ("administratif", "Administratif"),
                    ("technique", "Technique"),
                    ("promotion", "Promotion"),
                    ("investissement", "Investissement"),
                    ("fonciere", "Foncière"),
                    ("financier", "Financier"),
                ],
                default="",
                max_length=100,
                verbose_name="Pôle",
            ),
        ),
    ]
