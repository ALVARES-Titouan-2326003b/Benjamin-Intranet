from django.db import migrations


def ensure_history_table(apps, schema_editor):
    TechnicalProjectHistory = apps.get_model("technique", "TechnicalProjectHistory")
    existing_tables = schema_editor.connection.introspection.table_names()

    if TechnicalProjectHistory._meta.db_table in existing_tables:
        return

    schema_editor.create_model(TechnicalProjectHistory)


class Migration(migrations.Migration):

    dependencies = [
        ("technique", "0002_technicalprojecthistory"),
    ]

    operations = [
        migrations.RunPython(ensure_history_table, migrations.RunPython.noop),
    ]
