import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("invoices", "0005_invoice_poles_and_services"),
        ("technique", "0010_unify_admin_dossier_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="facture",
            name="dossier",
            field=models.ForeignKey(
                blank=True,
                db_column="dossier",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="technique.technicalproject",
            ),
        ),
    ]
