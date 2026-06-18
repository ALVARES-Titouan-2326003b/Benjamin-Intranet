from django.db import migrations, models
import django.db.models.deletion


def seed_default_category_and_backfill(apps, schema_editor):
    Category = apps.get_model("management", "CategorieDossierAdministratif")
    Dossier = apps.get_model("management", "AdministrativeProject")

    category, _ = Category.objects.get_or_create(
        nom="Non classé",
        defaults={"is_default": True},
    )
    Category.objects.exclude(pk=category.pk).filter(is_default=True).update(is_default=False)

    for dossier in Dossier.objects.all():
        changed_fields = []
        if not dossier.affaire:
            dossier.affaire = dossier.name
            changed_fields.append("affaire")
        if dossier.prix == 0 and dossier.total_estimated:
            dossier.prix = dossier.total_estimated
            changed_fields.append("prix")
        if not dossier.categorie_id:
            dossier.categorie = category
            changed_fields.append("categorie")
        if changed_fields:
            dossier.save(update_fields=changed_fields)


class Migration(migrations.Migration):
    dependencies = [
        ("management", "0005_gmail_conversation_journal"),
    ]

    operations = [
        migrations.CreateModel(
            name="CategorieDossierAdministratif",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nom", models.CharField(max_length=120, unique=True)),
                ("is_default", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "categorie_dossier_administratif",
                "ordering": ["nom"],
            },
        ),
        migrations.AddField(
            model_name="administrativeproject",
            name="acte",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="administrativeproject",
            name="adresse_bien",
            field=models.TextField(blank=True, verbose_name="Adresse du bien"),
        ),
        migrations.AddField(
            model_name="administrativeproject",
            name="affaire",
            field=models.CharField(blank=True, max_length=255, verbose_name="Affaire"),
        ),
        migrations.AddField(
            model_name="administrativeproject",
            name="activite_metier",
            field=models.CharField(
                choices=[
                    ("marchand_biens", "Marchands de bien"),
                    ("patrimoine", "Patrimoine"),
                ],
                default="marchand_biens",
                max_length=40,
            ),
        ),
        migrations.AddField(
            model_name="administrativeproject",
            name="beneficiaire",
            field=models.CharField(blank=True, max_length=255, verbose_name="Bénéficiaire"),
        ),
        migrations.AddField(
            model_name="administrativeproject",
            name="categorie",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="dossiers",
                to="management.categoriedossieradministratif",
            ),
        ),
        migrations.AddField(
            model_name="administrativeproject",
            name="cs_pret",
            field=models.TextField(blank=True, verbose_name="CS prêt"),
        ),
        migrations.AddField(
            model_name="administrativeproject",
            name="date_cs_pret",
            field=models.DateField(blank=True, null=True, verbose_name="Date CS prêt"),
        ),
        migrations.AddField(
            model_name="administrativeproject",
            name="date_dg",
            field=models.DateField(blank=True, null=True, verbose_name="Date DG"),
        ),
        migrations.AddField(
            model_name="administrativeproject",
            name="date_promesse",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="administrativeproject",
            name="date_reiteration",
            field=models.DateField(blank=True, null=True, verbose_name="Date de réitération"),
        ),
        migrations.AddField(
            model_name="administrativeproject",
            name="dg",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name="DG"),
        ),
        migrations.AddField(
            model_name="administrativeproject",
            name="etat",
            field=models.CharField(
                choices=[
                    ("promesse", "En cours de promesse"),
                    ("vendu", "Vendu"),
                    ("achete", "Acheté"),
                    ("attente", "En attente"),
                    ("signe", "Signé"),
                    ("annule", "Annulé"),
                    ("archive", "Archivé"),
                ],
                default="promesse",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="administrativeproject",
            name="frais",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="administrativeproject",
            name="locataire",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="administrativeproject",
            name="lot_etage",
            field=models.CharField(blank=True, max_length=120, verbose_name="Lot / étage"),
        ),
        migrations.AddField(
            model_name="administrativeproject",
            name="negociation_externe",
            field=models.TextField(blank=True, verbose_name="Négociation externe"),
        ),
        migrations.AddField(
            model_name="administrativeproject",
            name="prix",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="administrativeproject",
            name="type_dossier",
            field=models.CharField(
                choices=[("vente", "Vente"), ("acquisition", "Acquisition")],
                default="vente",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="administrativeproject",
            name="vendeur",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="administrativeproject",
            name="name",
            field=models.CharField(max_length=255, verbose_name="Nom du dossier"),
        ),
        migrations.AlterField(
            model_name="administrativeproject",
            name="reference",
            field=models.CharField(max_length=50, unique=True, verbose_name="Référence dossier"),
        ),
        migrations.RunPython(seed_default_category_and_backfill, migrations.RunPython.noop),
    ]
