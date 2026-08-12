from django.db import migrations


def remove_legacy_activity_type_schema(apps, schema_editor):
    """Répare les bases où la migration 0022 a été marquée sans modifier le schéma."""
    connection = schema_editor.connection
    quote_name = connection.ops.quote_name

    with connection.cursor() as cursor:
        tables = set(connection.introspection.table_names(cursor))

        if "activite" in tables:
            columns = {
                column.name
                for column in connection.introspection.get_table_description(cursor, "activite")
            }
            if "type" in columns:
                schema_editor.execute(
                    f"ALTER TABLE {quote_name('activite')} "
                    f"DROP COLUMN {quote_name('type')}"
                )

        if "type_activite" in tables:
            schema_editor.execute(f"DROP TABLE {quote_name('type_activite')}")


class Migration(migrations.Migration):
    dependencies = [
        ("management", "0024_custom_activity_time_slots"),
    ]

    operations = [
        migrations.RunPython(
            remove_legacy_activity_type_schema,
            migrations.RunPython.noop,
        ),
    ]
