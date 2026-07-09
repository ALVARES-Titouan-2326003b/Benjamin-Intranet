from django.db import migrations


def reset_tampon_id_sequence(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT setval(
                pg_get_serial_sequence('"tampon"', 'id'),
                COALESCE((SELECT MAX(id) FROM "tampon"), 1),
                (SELECT COUNT(*) > 0 FROM "tampon")
            )
            """
        )


class Migration(migrations.Migration):

    dependencies = [
        ("signatures", "0002_signature_modes_and_company_stamps"),
    ]

    operations = [
        migrations.RunPython(reset_tampon_id_sequence, migrations.RunPython.noop),
    ]
