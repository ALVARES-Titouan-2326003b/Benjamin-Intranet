# Generated for Module 1 administratif improvements.

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("management", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="activite",
            name="titre",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="activite",
            name="statut",
            field=models.CharField(
                choices=[
                    ("todo", "À faire"),
                    ("in_progress", "En cours"),
                    ("done", "Terminé"),
                    ("cancelled", "Annulé"),
                ],
                default="todo",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="activite",
            name="priorite",
            field=models.CharField(
                choices=[
                    ("low", "Basse"),
                    ("normal", "Normale"),
                    ("high", "Haute"),
                    ("urgent", "Urgente"),
                ],
                default="normal",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="activite",
            name="responsable",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="activites_assignees",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="activite",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="activites_creees",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="activite",
            name="updated_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="activites_modifiees",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="activite",
            name="client",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="activite",
            name="contact_externe",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="activite",
            name="outlook_event_id",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="activite",
            name="created_at",
            field=models.DateTimeField(default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="activite",
            name="updated_at",
            field=models.DateTimeField(default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.CreateModel(
            name="HistoriqueRappelActivite",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "canal",
                    models.CharField(
                        choices=[("email", "E-mail"), ("interne", "Notification interne")],
                        max_length=20,
                    ),
                ),
                ("destinataire", models.CharField(blank=True, max_length=255)),
                ("jours_avant_echeance", models.IntegerField()),
                (
                    "statut",
                    models.CharField(
                        choices=[("sent", "Envoyé"), ("failed", "Échec")],
                        max_length=20,
                    ),
                ),
                ("erreur", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "activite",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="rappels",
                        to="management.activite",
                    ),
                ),
            ],
            options={
                "db_table": "historique_rappel_activite",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="NotificationInterne",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("titre", models.CharField(max_length=255)),
                ("message", models.TextField()),
                ("is_read", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "activite",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notifications",
                        to="management.activite",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notifications_internes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "notification_interne",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="historiquerappelactivite",
            constraint=models.UniqueConstraint(
                fields=("activite", "canal", "destinataire", "jours_avant_echeance"),
                name="uniq_rappel_activite_canal_dest_jour",
            ),
        ),
    ]
