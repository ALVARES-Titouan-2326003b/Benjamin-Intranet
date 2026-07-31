from django.db import migrations


def synchronize_activity_companies(apps, schema_editor):
    Activity = apps.get_model("management", "Activite")
    Project = apps.get_model("technique", "TechnicalProject")
    for project_id, company_id in Project.objects.values_list("pk", "societe_id").iterator():
        Activity.objects.filter(dossier_id=project_id).update(societe_id=company_id)


class Migration(migrations.Migration):
    dependencies = [
        ("management", "0022_remove_activite_type_and_typeactivite"),
        ("technique", "0014_require_project_company"),
    ]

    operations = [
        migrations.RunPython(
            synchronize_activity_companies,
            migrations.RunPython.noop,
        ),
    ]
