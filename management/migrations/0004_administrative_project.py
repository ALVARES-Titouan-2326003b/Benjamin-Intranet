import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def copy_existing_activity_projects(apps, schema_editor):
    Activite = apps.get_model("management", "Activite")
    AdministrativeProject = apps.get_model("management", "AdministrativeProject")
    TechnicalProject = apps.get_model("technique", "TechnicalProject")

    project_ids = (
        Activite.objects.exclude(dossier_id__isnull=True)
        .values_list("dossier_id", flat=True)
        .distinct()
    )

    for project_id in project_ids:
        if AdministrativeProject.objects.filter(pk=project_id).exists():
            continue

        technical_project = TechnicalProject.objects.filter(pk=project_id).first()
        if technical_project:
            project_type = technical_project.type
            if project_type not in {"client", "juridique"}:
                project_type = "client"
            AdministrativeProject.objects.create(
                id=project_id,
                reference=technical_project.reference,
                name=technical_project.name,
                type=project_type,
                total_estimated=technical_project.total_estimated,
            )
        else:
            AdministrativeProject.objects.create(
                id=project_id,
                reference=f"ADM-{project_id}",
                name=f"Projet administratif {project_id}",
                type="interne",
                total_estimated=0,
            )


class Migration(migrations.Migration):

    dependencies = [
        ("management", "0003_alter_activite_client_alter_activite_contact_externe_and_more"),
        ("technique", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AdministrativeProject",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reference", models.CharField(max_length=50, unique=True, verbose_name="Référence projet")),
                ("name", models.CharField(max_length=255, verbose_name="Nom du projet")),
                (
                    "type",
                    models.CharField(
                        choices=[("client", "Client"), ("juridique", "Juridique"), ("interne", "Interne")],
                        default="client",
                        max_length=20,
                    ),
                ),
                (
                    "total_estimated",
                    models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name="Budget estimé"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="admin_projects_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="admin_projects_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "administrative_project",
                "ordering": ["reference"],
            },
        ),
        migrations.RunPython(copy_existing_activity_projects, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="activite",
            name="dossier",
            field=models.ForeignKey(
                db_column="dossier",
                on_delete=django.db.models.deletion.CASCADE,
                to="management.administrativeproject",
            ),
        ),
    ]
