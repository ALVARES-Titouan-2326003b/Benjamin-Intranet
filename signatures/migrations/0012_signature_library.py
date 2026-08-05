from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def name_existing_signatures(apps, schema_editor):
    SignatureUser = apps.get_model("signatures", "SignatureUser")
    for signature in SignatureUser.objects.select_related("user"):
        user = signature.user
        full_name = " ".join(
            value.strip()
            for value in (user.first_name or "", user.last_name or "")
            if value.strip()
        )
        signature.name = full_name or user.username
        signature.save(update_fields=["name"])


class Migration(migrations.Migration):
    dependencies = [
        ("signatures", "0011_multi_signer_workflows"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="signaturerequest",
            name="unique_signer_per_signature_workflow",
        ),
        migrations.RemoveField(model_name="signaturerequest", name="signed_by"),
        migrations.RemoveField(model_name="signaturerequest", name="sequence"),
        migrations.RemoveField(model_name="signaturerequest", name="workflow_id"),
        migrations.AlterField(
            model_name="signatureuser",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="signature_profiles",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="signatureuser",
            name="name",
            field=models.CharField(default="", max_length=120, verbose_name="Nom du signataire"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="signatureuser",
            name="is_active",
            field=models.BooleanField(default=True, verbose_name="Active"),
        ),
        migrations.RunPython(name_existing_signatures, migrations.RunPython.noop),
        migrations.AddField(
            model_name="document",
            name="signature_profile",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="documents_signes",
                to="signatures.signatureuser",
                verbose_name="Signature apposée",
            ),
        ),
        migrations.AddField(
            model_name="signaturerequest",
            name="signature_profile",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="demandes_signature",
                to="signatures.signatureuser",
                verbose_name="Signature à apposer",
            ),
        ),
        migrations.AlterModelOptions(
            name="signatureuser",
            options={"ordering": ["name", "pk"]},
        ),
        migrations.AlterModelOptions(name="signaturerequest", options={}),
    ]
