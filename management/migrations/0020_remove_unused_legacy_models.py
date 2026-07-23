from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("management", "0019_remove_recruitment_tables"),
    ]

    operations = [
        migrations.DeleteModel(name="AdministrativeProject"),
        migrations.DeleteModel(name="Pole"),
        migrations.DeleteModel(name="TelClient"),
    ]
