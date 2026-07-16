from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("management", "0014_custom_admin_field_activity_scope"),
        ("technique", "0011_projectexpense_facture"),
    ]

    operations = [
        migrations.AlterField(
            model_name="activite",
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
