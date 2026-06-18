from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("management", "0004_administrative_project"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="GmailConversation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("thread_id", models.CharField(max_length=255)),
                ("initial_message_id", models.CharField(blank=True, default="", max_length=255)),
                ("last_message_id", models.CharField(blank=True, default="", max_length=255)),
                ("subject", models.CharField(blank=True, default="", max_length=500)),
                ("recipient", models.EmailField(blank=True, default="", max_length=254)),
                ("preview", models.TextField(blank=True, default="")),
                ("status", models.CharField(choices=[("open", "Ouvert"), ("reminded", "Relancé"), ("replied", "Répondu")], default="open", max_length=20)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("last_reminded_at", models.DateTimeField(blank=True, null=True)),
                ("last_synced_at", models.DateTimeField(blank=True, null=True)),
                ("replied_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="gmail_conversations", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "gmail_conversation", "ordering": ["-sent_at", "-updated_at"]},
        ),
        migrations.AddConstraint(
            model_name="gmailconversation",
            constraint=models.UniqueConstraint(fields=("owner", "thread_id"), name="uniq_gmail_conversation_owner_thread"),
        ),
        migrations.CreateModel(
            name="GmailConversationEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(choices=[("synced", "Synchronisation"), ("reminder_sent", "Relance envoyée"), ("status_changed", "Statut modifié"), ("reply_detected", "Réponse détectée"), ("note", "Note"), ("error", "Erreur")], max_length=30)),
                ("old_status", models.CharField(blank=True, default="", max_length=20)),
                ("new_status", models.CharField(blank=True, default="", max_length=20)),
                ("note", models.TextField(blank=True, default="")),
                ("external_message_id", models.CharField(blank=True, default="", max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("conversation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="events", to="management.gmailconversation")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="gmail_conversation_events", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "gmail_conversation_event", "ordering": ["-created_at", "-id"]},
        ),
    ]
