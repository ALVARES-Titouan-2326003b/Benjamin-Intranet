from django.db import migrations


def create_executive_assistant_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.get_or_create(name="ASSISTANTE_DIRECTION")


class Migration(migrations.Migration):
    dependencies = [
        ("invoices", "0013_relabel_invoice_service_as_pole"),
    ]

    operations = [
        migrations.RunPython(create_executive_assistant_group, migrations.RunPython.noop),
    ]
