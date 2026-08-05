from django.db import migrations, models


def copy_existing_documents(apps, schema_editor):
    KeyDate = apps.get_model("technique", "TechnicalProjectKeyDate")
    through = KeyDate.documents.through
    links = [
        through(technicalprojectkeydate_id=key_date.pk, documenttechnique_id=key_date.document_id)
        for key_date in KeyDate.objects.exclude(document_id__isnull=True).iterator()
    ]
    through.objects.bulk_create(links, ignore_conflicts=True)


class Migration(migrations.Migration):
    dependencies = [
        ("technique", "0014_require_project_company"),
    ]

    operations = [
        migrations.AddField(
            model_name="technicalprojectkeydate",
            name="documents",
            field=models.ManyToManyField(
                blank=True,
                related_name="key_dates_multiple",
                to="technique.documenttechnique",
                verbose_name="Documents liés",
            ),
        ),
        migrations.RunPython(copy_existing_documents, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="technicalprojectkeydate",
            name="document",
        ),
        migrations.AlterField(
            model_name="technicalprojectkeydate",
            name="documents",
            field=models.ManyToManyField(
                blank=True,
                related_name="key_dates",
                to="technique.documenttechnique",
                verbose_name="Documents liés",
            ),
        ),
    ]
