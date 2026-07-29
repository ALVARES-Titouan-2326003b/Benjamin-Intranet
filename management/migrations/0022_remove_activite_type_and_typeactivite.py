from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("management", "0021_reset_admin_category_sequence"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="activite",
            name="type",
        ),
        migrations.DeleteModel(
            name="TypeActivite",
        ),
    ]
