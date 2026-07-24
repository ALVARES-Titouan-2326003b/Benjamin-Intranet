from django.db import migrations


RESET_CATEGORY_SEQUENCE_SQL = """
SELECT setval(
    pg_get_serial_sequence('categorie_dossier_administratif', 'id'),
    COALESCE(MAX(id), 1),
    MAX(id) IS NOT NULL
)
FROM categorie_dossier_administratif;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("management", "0020_remove_unused_legacy_models"),
    ]

    operations = [
        migrations.RunSQL(
            sql=RESET_CATEGORY_SEQUENCE_SQL,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
