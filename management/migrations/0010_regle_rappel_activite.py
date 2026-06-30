from django.db import migrations, models


def seed_default_activity_reminder_rules(apps, schema_editor):
    Rule = apps.get_model("management", "RegleRappelActivite")
    for days in (10, 7, 4, 1):
        Rule.objects.get_or_create(
            timing="before",
            days=days,
            defaults={"is_active": True},
        )


class Migration(migrations.Migration):
    dependencies = [
        ("management", "0009_promotion_immobiliere_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="RegleRappelActivite",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "timing",
                    models.CharField(
                        choices=[("before", "Avant l’échéance"), ("after", "Après l’échéance")],
                        default="before",
                        max_length=10,
                    ),
                ),
                ("days", models.PositiveSmallIntegerField(default=1)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "regle_rappel_activite",
                "ordering": ["timing", "days"],
            },
        ),
        migrations.AddConstraint(
            model_name="reglerappelactivite",
            constraint=models.UniqueConstraint(
                fields=("timing", "days"),
                name="uniq_regle_rappel_activite_timing_days",
            ),
        ),
        migrations.RunPython(seed_default_activity_reminder_rules, migrations.RunPython.noop),
    ]
