from django.db import migrations, models
import django.db.models.deletion


def link_documents_to_projects(apps, schema_editor):
    DocumentTechnique = apps.get_model("technique", "DocumentTechnique")
    TechnicalProject = apps.get_model("technique", "TechnicalProject")

    projects = list(TechnicalProject.objects.all())
    by_reference = {project.reference.strip().lower(): project for project in projects}
    by_name = {project.name.strip().lower(): project for project in projects}
    by_label = {
        f"{project.reference} - {project.name}".strip().lower(): project
        for project in projects
    }

    for document in DocumentTechnique.objects.all():
        raw_label = (getattr(document, "projet", "") or "").strip()
        if not raw_label:
            continue

        key = raw_label.lower()
        project = by_label.get(key) or by_reference.get(key) or by_name.get(key)

        if project is None and " - " in raw_label:
            reference = raw_label.split(" - ", 1)[0].strip().lower()
            project = by_reference.get(reference)

        if project is not None:
            document.project_id = project.pk
            document.save(update_fields=["project"])


def restore_project_label(apps, schema_editor):
    DocumentTechnique = apps.get_model("technique", "DocumentTechnique")

    for document in DocumentTechnique.objects.select_related("project"):
        if document.project_id:
            document.projet = f"{document.project.reference} - {document.project.name}"
            document.save(update_fields=["projet"])


class Migration(migrations.Migration):

    dependencies = [
        ("technique", "0007_technicalprojecthistory_status_updated"),
    ]

    operations = [
        migrations.AddField(
            model_name="documenttechnique",
            name="project",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="documents",
                to="technique.technicalproject",
                verbose_name="Dossier associé",
            ),
        ),
        migrations.RunPython(link_documents_to_projects, restore_project_label),
        migrations.RemoveField(
            model_name="documenttechnique",
            name="projet",
        ),
        migrations.RemoveField(
            model_name="documenttechnique",
            name="type_document",
        ),
    ]
