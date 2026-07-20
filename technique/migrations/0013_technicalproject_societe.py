import django.db.models.deletion
from django.db import migrations, models


def infer_project_companies(apps, schema_editor):
    Project = apps.get_model("technique", "TechnicalProject")
    Facture = apps.get_model("invoices", "Facture")
    for project in Project.objects.all().iterator():
        company_ids = list(
            Facture.objects.filter(dossier_id=project.pk, societe_id__isnull=False)
            .values_list("societe_id", flat=True)
            .distinct()[:2]
        )
        if len(company_ids) == 1:
            project.societe_id = company_ids[0]
            project.save(update_fields=["societe"])


class Migration(migrations.Migration):
    dependencies = [
        ("invoices", "0008_societe_referential"),
        ("technique", "0012_technicalproject_archiving"),
    ]
    operations = [
        migrations.AddField(
            model_name="technicalproject",
            name="societe",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="dossiers", to="invoices.societe", verbose_name="Société"),
        ),
        migrations.RunPython(infer_project_companies, migrations.RunPython.noop),
    ]
