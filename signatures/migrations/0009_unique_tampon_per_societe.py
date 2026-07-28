import django.db.models.deletion
from django.db import migrations, models


def merge_duplicate_company_stamps(apps, schema_editor):
    Document = apps.get_model("signatures", "Document")
    SignatureRequest = apps.get_model("signatures", "SignatureRequest")
    Tampon = apps.get_model("signatures", "Tampon")

    duplicate_company_ids = (
        Tampon.objects.values("societe_id")
        .annotate(stamp_count=models.Count("id"))
        .filter(stamp_count__gt=1)
        .values_list("societe_id", flat=True)
    )

    for company_id in duplicate_company_ids.iterator():
        stamps = list(Tampon.objects.filter(societe_id=company_id).order_by("pk"))
        stamp_to_keep = next((stamp for stamp in stamps if stamp.is_active), stamps[0])
        duplicate_ids = [stamp.pk for stamp in stamps if stamp.pk != stamp_to_keep.pk]

        Document.objects.filter(tampon_id__in=duplicate_ids).update(
            tampon_id=stamp_to_keep.pk
        )
        SignatureRequest.objects.filter(tampon_id__in=duplicate_ids).update(
            tampon_id=stamp_to_keep.pk
        )
        Tampon.objects.filter(pk__in=duplicate_ids).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("signatures", "0008_signature_mentions"),
    ]

    operations = [
        migrations.RunPython(
            merge_duplicate_company_stamps,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="tampon",
            name="societe",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="tampon",
                to="invoices.societe",
                verbose_name="Société",
            ),
        ),
    ]
