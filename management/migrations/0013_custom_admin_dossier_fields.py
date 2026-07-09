from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("management", "0012_activite_use_unified_dossier"),
        ("technique", "0011_projectexpense_facture"),
    ]

    operations = [
        migrations.CreateModel(
            name="ChampPersonnaliseDossier",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label", models.CharField(max_length=120, unique=True, verbose_name="Libellé")),
                (
                    "field_type",
                    models.CharField(
                        choices=[
                            ("text", "Texte"),
                            ("date", "Date"),
                            ("amount", "Montant"),
                            ("number", "Nombre"),
                            ("checkbox", "Case à cocher"),
                            ("choice", "Liste de choix"),
                        ],
                        default="text",
                        max_length=20,
                        verbose_name="Type de saisie",
                    ),
                ),
                ("choices", models.TextField(blank=True, verbose_name="Choix possibles")),
                ("show_in_detail", models.BooleanField(default=True, verbose_name="Afficher dans la fiche dossier")),
                ("show_in_table", models.BooleanField(default=False, verbose_name="Afficher dans le tableau")),
                ("is_active", models.BooleanField(default=True, verbose_name="Actif")),
                ("sort_order", models.PositiveSmallIntegerField(default=0, verbose_name="Ordre")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "champ_personnalise_dossier",
                "ordering": ["sort_order", "label"],
            },
        ),
        migrations.CreateModel(
            name="ValeurChampPersonnaliseDossier",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("value", models.TextField(blank=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "dossier",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="custom_field_values",
                        to="technique.technicalproject",
                    ),
                ),
                (
                    "field",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="values",
                        to="management.champpersonnalisedossier",
                    ),
                ),
            ],
            options={
                "db_table": "valeur_champ_personnalise_dossier",
            },
        ),
        migrations.AddConstraint(
            model_name="valeurchamppersonnalisedossier",
            constraint=models.UniqueConstraint(
                fields=("dossier", "field"),
                name="uniq_valeur_champ_personnalise_dossier",
            ),
        ),
    ]
