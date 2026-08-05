import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("signatures", "0010_signature_place_and_date"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="signaturerequest",
            name="workflow_id",
            field=models.UUIDField(db_index=True, default=uuid.uuid4),
        ),
        migrations.AddField(
            model_name="signaturerequest",
            name="sequence",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="signaturerequest",
            name="signed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="signatures_effectivement_apposees",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddConstraint(
            model_name="signaturerequest",
            constraint=models.UniqueConstraint(
                fields=("workflow_id", "approver"),
                name="unique_signer_per_signature_workflow",
            ),
        ),
        migrations.AlterModelOptions(
            name="signaturerequest",
            options={"ordering": ["sequence", "created_at"]},
        ),
    ]
