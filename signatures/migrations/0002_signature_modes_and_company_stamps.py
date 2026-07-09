from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("signatures", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="tampon",
            name="societe",
            field=models.CharField(default="Benjamin Immobilier", max_length=200, verbose_name="Société"),
        ),
        migrations.AddField(
            model_name="tampon",
            name="is_active",
            field=models.BooleanField(default=True, verbose_name="Actif"),
        ),
        migrations.AlterModelOptions(
            name="tampon",
            options={"ordering": ["societe", "nom"]},
        ),
        migrations.AddField(
            model_name="document",
            name="signature_mode",
            field=models.CharField(
                choices=[
                    ("signature", "Signature seule"),
                    ("stamp_signature", "Tampon + signature"),
                ],
                default="stamp_signature",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="document",
            name="tampon",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="documents_signes",
                to="signatures.tampon",
            ),
        ),
        migrations.AddField(
            model_name="signaturerequest",
            name="signature_mode",
            field=models.CharField(
                choices=[
                    ("signature", "Signature seule"),
                    ("stamp_signature", "Tampon + signature"),
                ],
                default="stamp_signature",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="signaturerequest",
            name="tampon",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="demandes_signature",
                to="signatures.tampon",
            ),
        ),
    ]
