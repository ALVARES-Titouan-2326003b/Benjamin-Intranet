from django.db import migrations, models


def ensure_invoice_pole_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for name in [
        "POLE_FINANCIER",
        "POLE_TECHNIQUE",
        "POLE_ADMINISTRATIF",
        "POLE_PROMOTION",
        "POLE_DEVELOPPEMENT",
        "POLE_INVESTISSEMENT",
        "CEO",
        "COLLABORATEUR",
    ]:
        Group.objects.get_or_create(name=name)


class Migration(migrations.Migration):

    dependencies = [
        ("invoices", "0004_facture_affaire_facture_commentaire_compta_and_more"),
        ("auth", "0012_alter_user_first_name_max_length"),
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
            ),
        ),
        migrations.RunPython(ensure_invoice_pole_groups, migrations.RunPython.noop),
    ]
