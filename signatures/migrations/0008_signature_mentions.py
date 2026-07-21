from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("signatures", "0007_signaturerequest_page_number"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="signature_mention",
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AddField(
            model_name="signaturerequest",
            name="signature_mention",
            field=models.CharField(blank=True, max_length=160),
        ),
    ]
