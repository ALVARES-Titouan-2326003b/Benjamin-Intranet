import django.db.models.deletion
from django.db import migrations, models


def inherit_project_company(apps, schema_editor):
    Activity = apps.get_model("management", "Activite")
    for activity in Activity.objects.filter(dossier_id__isnull=False).iterator():
        activity.societe_id = activity.dossier.societe_id
        if activity.societe_id:
            activity.save(update_fields=["societe"])


class Migration(migrations.Migration):
    dependencies = [
        ("invoices", "0008_societe_referential"),
        ("management", "0015_optional_activity_dossier"),
        ("technique", "0013_technicalproject_societe"),
    ]
    operations = [
        migrations.AddField(
            model_name="activite",
            name="societe",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="activites", to="invoices.societe", verbose_name="Société"),
        ),
        migrations.RunPython(inherit_project_company, migrations.RunPython.noop),
    ]
