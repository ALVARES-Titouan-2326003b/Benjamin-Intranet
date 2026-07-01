from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("management", "0010_regle_rappel_activite"),
    ]

    operations = [
        migrations.AddField(
            model_name="activite",
            name="duree_minutes",
            field=models.PositiveSmallIntegerField(
                choices=[(30, "30 min"), (60, "1 h"), (90, "1 h 30"), (120, "2 h")],
                default=60,
                verbose_name="Durée du créneau",
            ),
        ),
    ]
