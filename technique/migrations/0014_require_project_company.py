import django.db.models.deletion
from django.db import migrations, models


FALLBACK_COMPANY_NAME = "Société à affecter"


def assign_and_synchronize_companies(apps, schema_editor):
    Project = apps.get_model("technique", "TechnicalProject")
    Company = apps.get_model("invoices", "Societe")
    Invoice = apps.get_model("invoices", "Facture")

    fallback_company = None
    for project in Project.objects.filter(societe_id__isnull=True).iterator():
        company_ids = list(
            Invoice.objects.filter(dossier_id=project.pk, societe_id__isnull=False)
            .values_list("societe_id", flat=True)
            .distinct()[:2]
        )
        if len(company_ids) == 1:
            company_id = company_ids[0]
        else:
            if fallback_company is None:
                fallback_company, _ = Company.objects.get_or_create(
                    nom=FALLBACK_COMPANY_NAME,
                    defaults={"is_active": True},
                )
            company_id = fallback_company.pk
        Project.objects.filter(pk=project.pk).update(societe_id=company_id)

    for project_id, company_id, reference, name in Project.objects.values_list(
        "pk",
        "societe_id",
        "reference",
        "name",
    ).iterator():
        Invoice.objects.filter(dossier_id=project_id).update(
            societe_id=company_id,
            affaire=f"{reference} - {name}",
        )


class Migration(migrations.Migration):
    dependencies = [
        ("technique", "0013_technicalproject_societe"),
    ]

    operations = [
        migrations.RunPython(
            assign_and_synchronize_companies,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="technicalproject",
            name="societe",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="dossiers",
                to="invoices.societe",
                verbose_name="Société",
            ),
        ),
    ]
