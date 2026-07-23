from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("invoices", "0008_societe_referential"),
    ]

    operations = [
        migrations.DeleteModel(name="ClientDossier"),
        migrations.DeleteModel(name="TelFournisseur"),
    ]
