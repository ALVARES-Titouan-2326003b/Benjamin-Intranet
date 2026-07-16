from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("signatures", "0004_document_uploaded_by"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="tampon",
            options={"ordering": ["societe"]},
        ),
        migrations.RemoveField(
            model_name="tampon",
            name="nom",
        ),
    ]
