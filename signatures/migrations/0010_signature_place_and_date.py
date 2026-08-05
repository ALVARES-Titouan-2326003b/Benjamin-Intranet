from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("signatures", "0009_unique_tampon_per_societe"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="signature_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="document",
            name="signature_place",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="signaturerequest",
            name="signature_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="signaturerequest",
            name="signature_place",
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
