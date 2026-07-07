import django.db.models.deletion
from django.db import migrations, models


def add_facture_column_if_missing(apps, schema_editor):
    table_name = "depense_projet"
    column_name = "facture_id"

    with schema_editor.connection.cursor() as cursor:
        existing_columns = {
            column.name
            for column in schema_editor.connection.introspection.get_table_description(
                cursor,
                table_name,
            )
        }

    if column_name in existing_columns:
        return

    ProjectExpense = apps.get_model("technique", "ProjectExpense")
    Facture = apps.get_model("invoices", "Facture")
    field = models.OneToOneField(
        Facture,
        blank=True,
        null=True,
        on_delete=django.db.models.deletion.SET_NULL,
        related_name="project_expense",
        verbose_name="Facture associée",
    )
    field.set_attributes_from_name("facture")
    schema_editor.add_field(ProjectExpense, field)


class Migration(migrations.Migration):

    dependencies = [
        ("technique", "0010_unify_admin_dossier_fields"),
        ("invoices", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    add_facture_column_if_missing,
                    reverse_code=migrations.RunPython.noop,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="projectexpense",
                    name="facture",
                    field=models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="project_expense",
                        to="invoices.facture",
                        verbose_name="Facture associée",
                    ),
                ),
            ],
        ),
    ]
