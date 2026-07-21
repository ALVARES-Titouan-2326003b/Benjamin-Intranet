from django.db import migrations, models


def use_last_page_for_existing_requests(apps, schema_editor):
    SignatureRequest = apps.get_model("signatures", "SignatureRequest")
    for request in SignatureRequest.objects.select_related("document").all():
        try:
            from pypdf import PdfReader

            request.page_number = len(PdfReader(request.document.fichier.path).pages)
        except Exception:
            request.page_number = 1
        request.save(update_fields=["page_number"])


class Migration(migrations.Migration):
    dependencies = [
        ("signatures", "0006_tampon_societe_referential"),
    ]

    operations = [
        migrations.AddField(
            model_name="signaturerequest",
            name="page_number",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.RunPython(use_last_page_for_existing_requests, migrations.RunPython.noop),
    ]
