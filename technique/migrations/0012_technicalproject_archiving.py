import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("technique", "0011_projectexpense_facture"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="technicalproject",
            name="archive_comment",
            field=models.TextField(blank=True, verbose_name="Commentaire d'archivage"),
        ),
        migrations.AddField(
            model_name="technicalproject",
            name="archived_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True, verbose_name="Archivé le"),
        ),
        migrations.AddField(
            model_name="technicalproject",
            name="archived_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="technical_dossiers_archived",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Archivé par",
            ),
        ),
        migrations.AlterField(
            model_name="technicalprojecthistory",
            name="action",
            field=models.CharField(
                choices=[
                    ("project_created", "Dossier créé"),
                    ("budget_updated", "Budget modifié"),
                    ("expense_created", "Dépense créée"),
                    ("expense_updated", "Dépense modifiée"),
                    ("expense_deleted", "Dépense supprimée"),
                    ("key_date_created", "Date clé créée"),
                    ("key_date_updated", "Date clé modifiée"),
                    ("key_date_deleted", "Date clé supprimée"),
                    ("action_created", "Action créée"),
                    ("action_updated", "Action modifiée"),
                    ("action_deleted", "Action supprimée"),
                    ("status_updated", "Statut modifié"),
                    ("project_archived", "Dossier archivé"),
                    ("project_restored", "Dossier restauré"),
                    ("project_deleted", "Dossier supprimé"),
                ],
                max_length=30,
                verbose_name="Action",
            ),
        ),
    ]
