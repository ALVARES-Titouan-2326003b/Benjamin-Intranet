from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("signatures", "0003_reset_tampon_id_sequence"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="uploaded_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="documents_signature_uploades",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
