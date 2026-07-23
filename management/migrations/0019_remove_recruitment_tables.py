from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("management", "0018_historique_relances_email"),
    ]

    operations = [
        migrations.RunSQL("DROP TABLE IF EXISTS candidature"),
        migrations.RunSQL("DROP TABLE IF EXISTS candidat"),
        migrations.RunSQL("DROP TABLE IF EXISTS fiche_de_poste"),
    ]
