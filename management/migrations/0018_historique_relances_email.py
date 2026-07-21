from django.db import migrations, models


def snapshot_existing_reminders(apps, schema_editor):
    Event = apps.get_model("management", "GmailConversationEvent")
    for event in Event.objects.filter(event_type="reminder_sent").select_related("conversation"):
        event.reminder_source = "legacy"
        event.reminder_subject = event.conversation.subject
        event.reminder_recipient = event.conversation.recipient
        event.save(
            update_fields=[
                "reminder_source",
                "reminder_subject",
                "reminder_recipient",
            ]
        )


class Migration(migrations.Migration):
    dependencies = [
        ("management", "0017_rappels_individuels_activite"),
    ]

    operations = [
        migrations.AddField(
            model_name="gmailconversationevent",
            name="reminder_recipient",
            field=models.EmailField(blank=True, default="", max_length=254),
        ),
        migrations.AddField(
            model_name="gmailconversationevent",
            name="reminder_source",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "Non applicable"),
                    ("manual", "Manuelle"),
                    ("automatic", "Automatique"),
                    ("legacy", "Historique existant"),
                ],
                default="",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="gmailconversationevent",
            name="reminder_subject",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
        migrations.RunPython(snapshot_existing_reminders, migrations.RunPython.noop),
    ]
