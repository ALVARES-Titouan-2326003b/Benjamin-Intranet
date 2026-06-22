from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("management", "0008_seed_admin_project_categories"),
    ]

    operations = [
        migrations.AlterField(
            model_name="administrativeproject",
            name="activite_metier",
            field=models.CharField(
                choices=[
                    ("marchand_biens", "Marchands de bien"),
                    ("promotion_immobiliere", "Promotion immobilière"),
                    ("patrimoine", "Patrimoine"),
                ],
                default="marchand_biens",
                max_length=40,
            ),
        ),
        migrations.AlterField(
            model_name="administrativeproject",
            name="etat",
            field=models.CharField(
                choices=[
                    ("promesse", "En cours de promesse"),
                    ("vendu", "Vendu"),
                    ("achete", "Acheté"),
                ],
                default="promesse",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="administrativeproject",
            name="avenant_1",
            field=models.TextField(blank=True, verbose_name="Avenant 1"),
        ),
        migrations.AddField(
            model_name="administrativeproject",
            name="avenant_2",
            field=models.TextField(blank=True, verbose_name="Avenant 2"),
        ),
        migrations.AddField(
            model_name="administrativeproject",
            name="avenant_3",
            field=models.TextField(blank=True, verbose_name="Avenant 3"),
        ),
        migrations.AddField(
            model_name="administrativeproject",
            name="bornage",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="administrativeproject",
            name="depot_permis",
            field=models.DateField(blank=True, null=True, verbose_name="Dépôt permis"),
        ),
        migrations.AddField(
            model_name="administrativeproject",
            name="deuxieme_periode",
            field=models.CharField(blank=True, max_length=120, verbose_name="2ème période"),
        ),
        migrations.AddField(
            model_name="administrativeproject",
            name="diags",
            field=models.TextField(blank=True, verbose_name="Diags"),
        ),
        migrations.AddField(
            model_name="administrativeproject",
            name="etude_impact",
            field=models.TextField(blank=True, verbose_name="Étude d’impact"),
        ),
        migrations.AddField(
            model_name="administrativeproject",
            name="etude_pollution",
            field=models.TextField(blank=True, verbose_name="Étude pollution"),
        ),
        migrations.AddField(
            model_name="administrativeproject",
            name="etude_sol_geotechnique",
            field=models.TextField(blank=True, verbose_name="Étude sol / géotechnique"),
        ),
        migrations.AddField(
            model_name="administrativeproject",
            name="obtention_permis",
            field=models.DateField(blank=True, null=True, verbose_name="Obtention permis"),
        ),
        migrations.AddField(
            model_name="administrativeproject",
            name="parcelles",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="administrativeproject",
            name="premiere_periode",
            field=models.CharField(blank=True, max_length=120, verbose_name="1ère période"),
        ),
        migrations.AddField(
            model_name="administrativeproject",
            name="prorogation",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="administrativeproject",
            name="releves_compte",
            field=models.TextField(blank=True, verbose_name="Relevés de compte"),
        ),
    ]
