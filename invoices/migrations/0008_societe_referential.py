import django.db.models.deletion
from django.db import migrations, models


def migrate_invoice_companies(apps, schema_editor):
    Facture = apps.get_model("invoices", "Facture")
    Societe = apps.get_model("invoices", "Societe")

    for facture in Facture.objects.all().iterator():
        name = (facture.societe or "").strip()
        if not name:
            continue
        company = Societe.objects.filter(nom__iexact=name).first()
        if company is None:
            company = Societe.objects.create(nom=name)
        facture.societe_ref_id = company.pk
        facture.save(update_fields=["societe_ref"])


def restore_invoice_company_text(apps, schema_editor):
    Facture = apps.get_model("invoices", "Facture")
    for facture in Facture.objects.select_related("societe_ref").all().iterator():
        facture.societe = facture.societe_ref.nom if facture.societe_ref_id else ""
        facture.save(update_fields=["societe"])


class Migration(migrations.Migration):
    dependencies = [
        ("invoices", "0007_remove_cegid_export"),
    ]

    operations = [
        migrations.CreateModel(
            name="Societe",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nom", models.CharField(max_length=255, unique=True, verbose_name="Nom")),
                ("is_active", models.BooleanField(default=True, verbose_name="Active")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Créée le")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Modifiée le")),
            ],
            options={
                "verbose_name": "Société",
                "verbose_name_plural": "Sociétés",
                "db_table": "societe",
                "ordering": ["nom"],
            },
        ),
        migrations.AddField(
            model_name="facture",
            name="societe_ref",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="factures_migration",
                to="invoices.societe",
            ),
        ),
        migrations.RunPython(migrate_invoice_companies, restore_invoice_company_text),
        migrations.RemoveField(model_name="facture", name="societe"),
        migrations.RenameField(model_name="facture", old_name="societe_ref", new_name="societe"),
        migrations.AlterField(
            model_name="facture",
            name="societe",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="factures",
                to="invoices.societe",
                verbose_name="Société concernée",
            ),
        ),
    ]
