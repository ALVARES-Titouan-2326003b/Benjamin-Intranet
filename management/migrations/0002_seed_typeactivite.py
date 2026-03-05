from django.db import migrations


DEFAULT_TYPES_ACTIVITE = [
    "Vente",
    "Location",
    "Compromis",
    "Visite",
    "Relance",
    "Autre",
]

def forwards(apps, schema_editor):
    TypeActivite = apps.get_model("management", "TypeActivite")

    for t in DEFAULT_TYPES_ACTIVITE:
        TypeActivite.objects.get_or_create(type=t)

class Migration(migrations.Migration):

    dependencies = [
        ("management", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]