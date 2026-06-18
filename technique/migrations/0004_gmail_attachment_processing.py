from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("technique", "0003_ensure_technicalprojecthistory_table")]

    operations = [
        migrations.AddField(
            model_name="technicalemail",
            name="thread_id",
            field=models.CharField(blank=True, default="", max_length=255, verbose_name="Identifiant de conversation Gmail"),
        ),
        migrations.AddField(
            model_name="technicalemailattachment",
            name="processed_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Traité le"),
        ),
        migrations.AddField(
            model_name="technicalemailattachment",
            name="processing_error",
            field=models.TextField(blank=True, verbose_name="Erreur de traitement"),
        ),
        migrations.AddField(
            model_name="technicalemailattachment",
            name="processing_status",
            field=models.CharField(
                choices=[("pending", "En attente"), ("processing", "Traitement en cours"), ("linked", "Document créé"), ("skipped", "Ignoré"), ("error", "Erreur")],
                default="pending",
                max_length=20,
                verbose_name="État du traitement",
            ),
        ),
    ]
