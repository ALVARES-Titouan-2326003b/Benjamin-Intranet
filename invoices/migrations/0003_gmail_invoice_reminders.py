from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("invoices", "0002_finance_without_api"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="facturehistorique",
            name="days_overdue",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="facturehistorique",
            name="external_message_id",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="facturehistorique",
            name="recipient_email",
            field=models.EmailField(blank=True, default="", max_length=254),
        ),
        migrations.CreateModel(
            name="InvoiceReminderSettings",
            fields=[
                (
                    "id",
                    models.PositiveSmallIntegerField(
                        default=1, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "sender",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="invoice_reminder_settings",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Configuration des relances de factures",
                "verbose_name_plural": "Configuration des relances de factures",
                "db_table": "invoice_reminder_settings",
            },
        ),
    ]
