from django.db import migrations


def normalize_legacy_reminder_email(apps, schema_editor):
    """Keep legacy data while preventing the orphan column from blocking inserts."""
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        column_names = {
            column.name
            for column in connection.introspection.get_table_description(
                cursor, "facture"
            )
        }

    if "reminder_email" not in column_names:
        return

    table = schema_editor.quote_name("facture")
    column = schema_editor.quote_name("reminder_email")
    schema_editor.execute(
        f"ALTER TABLE {table} ALTER COLUMN {column} DROP NOT NULL"
    )
    schema_editor.execute(
        f"ALTER TABLE {table} ALTER COLUMN {column} SET DEFAULT ''"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("invoices", "0011_limit_invoice_statuses"),
    ]

    operations = [
        migrations.RunPython(normalize_legacy_reminder_email, migrations.RunPython.noop),
    ]
