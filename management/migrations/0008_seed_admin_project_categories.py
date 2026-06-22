from django.db import migrations


OFFICIAL_CATEGORIES = [
    "En cours d’acquisition",
    "En cours de vente",
    "Acheté",
    "Vendu",
    "Caduque",
    "Vente annulée",
    "Acquisition annulée",
    "Adjudication",
]


def seed_admin_project_categories(apps, schema_editor):
    Category = apps.get_model("management", "CategorieDossierAdministratif")

    categories = {}
    for index, name in enumerate(OFFICIAL_CATEGORIES):
        category, _ = Category.objects.get_or_create(
            nom=name,
            defaults={"is_default": index == 0},
        )
        categories[name] = category

    default_category = categories[OFFICIAL_CATEGORIES[0]]
    Category.objects.exclude(pk=default_category.pk).filter(is_default=True).update(is_default=False)
    if not default_category.is_default:
        default_category.is_default = True
        default_category.save(update_fields=["is_default"])


class Migration(migrations.Migration):
    dependencies = [
        ("management", "0007_remove_activite_client_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_admin_project_categories, migrations.RunPython.noop),
    ]
