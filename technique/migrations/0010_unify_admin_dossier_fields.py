from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


ADMIN_FIELD_NAMES = [
    "affaire",
    "lot_etage",
    "adresse_bien",
    "parcelles",
    "vendeur",
    "beneficiaire",
    "locataire",
    "type_dossier",
    "activite_metier",
    "etat",
    "categorie_id",
    "date_promesse",
    "premiere_periode",
    "deuxieme_periode",
    "avenant_1",
    "avenant_2",
    "avenant_3",
    "negociation_externe",
    "frais",
    "prix",
    "dg",
    "date_dg",
    "depot_permis",
    "obtention_permis",
    "diags",
    "bornage",
    "etude_sol_geotechnique",
    "etude_pollution",
    "etude_impact",
    "prorogation",
    "cs_pret",
    "date_cs_pret",
    "date_reiteration",
    "acte",
    "releves_compte",
]


def _default_category(Category):
    category = Category.objects.filter(is_default=True).first()
    if category:
        return category
    category, _ = Category.objects.get_or_create(
        nom="En cours d’acquisition",
        defaults={"is_default": True},
    )
    return category


def _technical_type_from_activity(value):
    return {
        "marchand_biens": "marchands_de_bien",
        "promotion_immobiliere": "promotion",
        "patrimoine": "patrimoine",
    }.get(value or "", "marchands_de_bien")


def _activity_from_technical_type(value):
    return {
        "marchands_de_bien": "marchand_biens",
        "promotion": "promotion_immobiliere",
        "patrimoine": "patrimoine",
    }.get(value or "", "marchand_biens")


def _admin_state_from_technical_status(value):
    return {
        "acquis": "achete",
        "promesse_signee": "promesse",
        "etude": "promesse",
    }.get(value or "", "promesse")


def copy_admin_projects_to_technical_projects(apps, schema_editor):
    TechnicalProject = apps.get_model("technique", "TechnicalProject")
    AdministrativeProject = apps.get_model("management", "AdministrativeProject")
    Category = apps.get_model("management", "CategorieDossierAdministratif")
    default_category = _default_category(Category)

    for project in TechnicalProject.objects.all():
        changed_fields = []
        if not project.affaire:
            project.affaire = project.name
            changed_fields.append("affaire")
        if not project.activite_metier:
            project.activite_metier = _activity_from_technical_type(project.type)
            changed_fields.append("activite_metier")
        if not project.etat:
            project.etat = _admin_state_from_technical_status(project.status)
            changed_fields.append("etat")
        if not project.categorie_id:
            project.categorie_id = default_category.pk
            changed_fields.append("categorie")
        if not project.prix and project.total_estimated:
            project.prix = project.total_estimated
            changed_fields.append("prix")
        if changed_fields:
            project.save(update_fields=changed_fields)

    for admin_project in AdministrativeProject.objects.select_related("categorie").all():
        reference = (admin_project.reference or "").strip().upper()
        if not reference:
            continue

        technical_project = TechnicalProject.objects.filter(reference=reference).first()
        if not technical_project:
            technical_project = TechnicalProject.objects.create(
                reference=reference,
                name=admin_project.name or admin_project.affaire or reference,
                type=_technical_type_from_activity(admin_project.activite_metier),
                status="etude",
                total_estimated=admin_project.total_estimated,
                created_by_id=admin_project.created_by_id,
                updated_by_id=admin_project.updated_by_id,
            )

        changed_fields = []
        for field_name in ADMIN_FIELD_NAMES:
            value = getattr(admin_project, field_name)
            setattr(technical_project, field_name, value)
            changed_fields.append("categorie" if field_name == "categorie_id" else field_name)

        if not technical_project.affaire:
            technical_project.affaire = admin_project.name
        if not technical_project.prix and admin_project.total_estimated:
            technical_project.prix = admin_project.total_estimated
        if not technical_project.total_estimated and admin_project.total_estimated:
            technical_project.total_estimated = admin_project.total_estimated
            changed_fields.append("total_estimated")
        if admin_project.created_by_id and not technical_project.created_by_id:
            technical_project.created_by_id = admin_project.created_by_id
            changed_fields.append("created_by")
        if admin_project.updated_by_id:
            technical_project.updated_by_id = admin_project.updated_by_id
            changed_fields.append("updated_by")

        technical_project.save(update_fields=sorted(set(changed_fields)))


class Migration(migrations.Migration):

    dependencies = [
        ("management", "0011_activite_duree_minutes"),
        ("technique", "0009_alter_technicalprojecthistory_action_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="technicalproject",
            name="acte",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="technicalproject",
            name="adresse_bien",
            field=models.TextField(blank=True, verbose_name="Adresse du bien"),
        ),
        migrations.AddField(
            model_name="technicalproject",
            name="affaire",
            field=models.CharField(blank=True, max_length=255, verbose_name="Affaire"),
        ),
        migrations.AddField(
            model_name="technicalproject",
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
        migrations.AddField(
            model_name="technicalproject",
            name="avenant_1",
            field=models.TextField(blank=True, verbose_name="Avenant 1"),
        ),
        migrations.AddField(
            model_name="technicalproject",
            name="avenant_2",
            field=models.TextField(blank=True, verbose_name="Avenant 2"),
        ),
        migrations.AddField(
            model_name="technicalproject",
            name="avenant_3",
            field=models.TextField(blank=True, verbose_name="Avenant 3"),
        ),
        migrations.AddField(
            model_name="technicalproject",
            name="beneficiaire",
            field=models.CharField(blank=True, max_length=255, verbose_name="Bénéficiaire"),
        ),
        migrations.AddField(
            model_name="technicalproject",
            name="bornage",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="technicalproject",
            name="categorie",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="technical_dossiers",
                to="management.categoriedossieradministratif",
            ),
        ),
        migrations.AddField(
            model_name="technicalproject",
            name="cs_pret",
            field=models.TextField(blank=True, verbose_name="CS prêt"),
        ),
        migrations.AddField(
            model_name="technicalproject",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name="technicalproject",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="technical_dossiers_created",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="technicalproject",
            name="date_cs_pret",
            field=models.DateField(blank=True, null=True, verbose_name="Date CS prêt"),
        ),
        migrations.AddField(
            model_name="technicalproject",
            name="date_dg",
            field=models.DateField(blank=True, null=True, verbose_name="Date DG"),
        ),
        migrations.AddField(
            model_name="technicalproject",
            name="date_promesse",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="technicalproject",
            name="date_reiteration",
            field=models.DateField(blank=True, null=True, verbose_name="Date de réitération"),
        ),
        migrations.AddField(
            model_name="technicalproject",
            name="depot_permis",
            field=models.DateField(blank=True, null=True, verbose_name="Dépôt permis"),
        ),
        migrations.AddField(
            model_name="technicalproject",
            name="deuxieme_periode",
            field=models.CharField(blank=True, max_length=120, verbose_name="2ème période"),
        ),
        migrations.AddField(
            model_name="technicalproject",
            name="dg",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name="DG"),
        ),
        migrations.AddField(
            model_name="technicalproject",
            name="diags",
            field=models.TextField(blank=True, verbose_name="Diags"),
        ),
        migrations.AddField(
            model_name="technicalproject",
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
            model_name="technicalproject",
            name="etude_impact",
            field=models.TextField(blank=True, verbose_name="Étude d’impact"),
        ),
        migrations.AddField(
            model_name="technicalproject",
            name="etude_pollution",
            field=models.TextField(blank=True, verbose_name="Étude pollution"),
        ),
        migrations.AddField(
            model_name="technicalproject",
            name="etude_sol_geotechnique",
            field=models.TextField(blank=True, verbose_name="Étude sol / géotechnique"),
        ),
        migrations.AddField(
            model_name="technicalproject",
            name="frais",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="technicalproject",
            name="locataire",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="technicalproject",
            name="lot_etage",
            field=models.CharField(blank=True, max_length=120, verbose_name="Lot / étage"),
        ),
        migrations.AddField(
            model_name="technicalproject",
            name="negociation_externe",
            field=models.TextField(blank=True, verbose_name="Négociation externe"),
        ),
        migrations.AddField(
            model_name="technicalproject",
            name="obtention_permis",
            field=models.DateField(blank=True, null=True, verbose_name="Obtention permis"),
        ),
        migrations.AddField(
            model_name="technicalproject",
            name="parcelles",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="technicalproject",
            name="premiere_periode",
            field=models.CharField(blank=True, max_length=120, verbose_name="1ère période"),
        ),
        migrations.AddField(
            model_name="technicalproject",
            name="prix",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="technicalproject",
            name="prorogation",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="technicalproject",
            name="releves_compte",
            field=models.TextField(blank=True, verbose_name="Relevés de compte"),
        ),
        migrations.AddField(
            model_name="technicalproject",
            name="type_dossier",
            field=models.CharField(
                choices=[("vente", "Vente"), ("acquisition", "Acquisition")],
                default="vente",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="technicalproject",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, null=True),
        ),
        migrations.AddField(
            model_name="technicalproject",
            name="updated_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="technical_dossiers_updated",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="technicalproject",
            name="vendeur",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.RunPython(copy_admin_projects_to_technical_projects, migrations.RunPython.noop),
    ]
