from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("management", "0013_custom_admin_dossier_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="champpersonnalisedossier",
            name="activite_metier",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "Toutes les activités"),
                    ("marchand_biens", "Marchands de bien"),
                    ("promotion_immobiliere", "Promotion immobilière"),
                    ("patrimoine", "Patrimoine"),
                ],
                default="",
                max_length=40,
                verbose_name="Activité métier",
            ),
        ),
    ]
