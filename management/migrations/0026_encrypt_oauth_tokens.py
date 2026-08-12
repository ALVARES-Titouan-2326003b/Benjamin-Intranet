from django.db import migrations

import config.fields


def transform_tokens(apps, schema_editor, transform):
    OAuthToken = apps.get_model("management", "OAuthToken")
    for token in OAuthToken.objects.all().iterator(chunk_size=200):
        OAuthToken.objects.filter(pk=token.pk).update(
            access_token=transform(token.access_token),
            refresh_token=transform(token.refresh_token),
        )


def encrypt_tokens(apps, schema_editor):
    transform_tokens(apps, schema_editor, config.fields.encrypt_value)


def decrypt_tokens(apps, schema_editor):
    transform_tokens(apps, schema_editor, config.fields.decrypt_value)


class Migration(migrations.Migration):
    dependencies = [("management", "0025_repair_legacy_activity_type_schema")]

    operations = [
        migrations.RunPython(encrypt_tokens, decrypt_tokens),
        migrations.AlterField(
            model_name="oauthtoken",
            name="access_token",
            field=config.fields.EncryptedTextField(),
        ),
        migrations.AlterField(
            model_name="oauthtoken",
            name="refresh_token",
            field=config.fields.EncryptedTextField(),
        ),
    ]
