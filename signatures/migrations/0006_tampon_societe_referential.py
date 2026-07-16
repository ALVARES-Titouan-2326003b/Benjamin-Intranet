import django.db.models.deletion
from django.db import migrations, models


def migrate_stamp_companies(apps, schema_editor):
    Societe = apps.get_model("invoices", "Societe")
    Tampon = apps.get_model("signatures", "Tampon")

    for tampon in Tampon.objects.all().iterator():
        name = (tampon.societe or "").strip() or "Benjamin Immobilier"
        company = Societe.objects.filter(nom__iexact=name).first()
        if company is None:
            company = Societe.objects.create(nom=name)
        tampon.societe_ref_id = company.pk
        tampon.save(update_fields=["societe_ref"])


def restore_stamp_company_text(apps, schema_editor):
    Tampon = apps.get_model("signatures", "Tampon")
    for tampon in Tampon.objects.select_related("societe_ref").all().iterator():
        tampon.societe = tampon.societe_ref.nom if tampon.societe_ref_id else "Benjamin Immobilier"
        tampon.save(update_fields=["societe"])


class Migration(migrations.Migration):
    dependencies = [
        ("invoices", "0008_societe_referential"),
        ("signatures", "0005_remove_tampon_nom"),
    ]

    operations = [
        migrations.AddField(
            model_name="tampon",
            name="societe_ref",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="tampons_migration",
                to="invoices.societe",
            ),
        ),
        migrations.RunPython(migrate_stamp_companies, restore_stamp_company_text),
        migrations.RemoveField(model_name="tampon", name="societe"),
        migrations.RenameField(model_name="tampon", old_name="societe_ref", new_name="societe"),
        migrations.AlterField(
            model_name="tampon",
            name="societe",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="tampons",
                to="invoices.societe",
                verbose_name="Société",
            ),
        ),
        migrations.AlterModelOptions(name="tampon", options={"ordering": ["societe__nom"]}),
    ]
