from django.db import migrations, models
import django.db.models.deletion


def migrate_activities_to_technical_dossiers(apps, schema_editor):
    Activite = apps.get_model("management", "Activite")
    AdministrativeProject = apps.get_model("management", "AdministrativeProject")
    TechnicalProject = apps.get_model("technique", "TechnicalProject")

    admin_by_id = {project.pk: project for project in AdministrativeProject.objects.all()}
    technical_by_reference = {
        project.reference: project
        for project in TechnicalProject.objects.all()
    }

    for activity in Activite.objects.all():
        old_dossier_id = activity.dossier_id
        admin_project = admin_by_id.get(old_dossier_id)
        target = None
        if admin_project:
            target = technical_by_reference.get(admin_project.reference)
        if target is None:
            target = TechnicalProject.objects.filter(pk=old_dossier_id).first()
        if target is None and admin_project:
            target = TechnicalProject.objects.create(
                reference=admin_project.reference,
                name=admin_project.name or admin_project.affaire or admin_project.reference,
                affaire=admin_project.affaire or admin_project.name,
                type_dossier=admin_project.type_dossier,
                activite_metier=admin_project.activite_metier,
                etat=admin_project.etat,
                categorie_id=admin_project.categorie_id,
                prix=admin_project.prix,
                total_estimated=admin_project.total_estimated,
            )
            technical_by_reference[target.reference] = target
        if target is not None:
            activity.dossier_tech_id = target.pk
            activity.save(update_fields=["dossier_tech"])


class Migration(migrations.Migration):

    dependencies = [
        ("management", "0011_activite_duree_minutes"),
        ("technique", "0010_unify_admin_dossier_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="activite",
            name="dossier_tech",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="technique.technicalproject",
            ),
        ),
        migrations.RunPython(
            migrate_activities_to_technical_dossiers,
            migrations.RunPython.noop,
        ),
        migrations.RemoveField(
            model_name="activite",
            name="dossier",
        ),
        migrations.RenameField(
            model_name="activite",
            old_name="dossier_tech",
            new_name="dossier",
        ),
        migrations.AlterField(
            model_name="activite",
            name="dossier",
            field=models.ForeignKey(
                db_column="dossier",
                on_delete=django.db.models.deletion.CASCADE,
                to="technique.technicalproject",
            ),
        ),
    ]
