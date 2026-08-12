from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("management", "0023_sync_activity_project_company"),
    ]

    operations = [
        migrations.AlterField(
            model_name="activite",
            name="duree_minutes",
            field=models.PositiveSmallIntegerField(
                default=60,
                verbose_name="Durée du créneau",
            ),
        ),
    ]
