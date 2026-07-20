from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("management", "0016_activite_societe"),
    ]

    operations = [
        migrations.CreateModel(
            name="RappelActivite",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "timing",
                    models.CharField(
                        choices=[("before", "Avant l’échéance"), ("after", "Après l’échéance")],
                        default="before",
                        max_length=10,
                    ),
                ),
                ("days", models.PositiveSmallIntegerField(default=1)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "activite",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="rappels_planifies",
                        to="management.activite",
                    ),
                ),
            ],
            options={
                "db_table": "rappel_activite",
                "ordering": ["timing", "days"],
            },
        ),
        migrations.AddConstraint(
            model_name="rappelactivite",
            constraint=models.UniqueConstraint(
                fields=("activite", "timing", "days"),
                name="uniq_rappel_individuel_activite_timing_days",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="historiquerappelactivite",
            name="uniq_rappel_activite_canal_dest_jour",
        ),
        migrations.AddField(
            model_name="historiquerappelactivite",
            name="contenu",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="historiquerappelactivite",
            name="date_echeance",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="historiquerappelactivite",
            name="objet",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddConstraint(
            model_name="historiquerappelactivite",
            constraint=models.UniqueConstraint(
                fields=("activite", "canal", "destinataire", "jours_avant_echeance", "date_echeance"),
                name="uniq_rappel_activite_canal_dest_jour",
            ),
        ),
    ]
