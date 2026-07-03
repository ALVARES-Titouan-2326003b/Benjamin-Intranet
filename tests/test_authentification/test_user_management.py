import pytest
from django.contrib.auth.models import Group, User
from django.db import connection
from django.urls import reverse


@pytest.mark.django_db
def test_superuser_can_delete_standard_user(client):
    Group.objects.get_or_create(name="CEO")
    actor = User.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="adminpass",
    )
    target = User.objects.create_user(
        username="target",
        email="target@example.com",
        password="targetpass",
    )

    client.force_login(actor)
    response = client.post(reverse("authentication:delete_user", args=[target.pk]))

    assert response.status_code == 302
    assert response.url == reverse("authentication:user_management")
    assert not User.objects.filter(pk=target.pk).exists()


@pytest.mark.django_db
def test_delete_user_removes_legacy_relance_followups(client):
    actor = User.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="adminpass",
    )
    target = User.objects.create_user(
        username="target",
        email="target@example.com",
        password="targetpass",
    )

    with connection.cursor() as cursor:
        cursor.execute('DROP TABLE IF EXISTS "relance_followup"')
        cursor.execute(
            'CREATE TABLE "relance_followup" ('
            '"id" integer PRIMARY KEY AUTOINCREMENT, '
            '"user_id" integer NOT NULL)'
        )
        cursor.execute(
            'INSERT INTO "relance_followup" ("user_id") VALUES (%s)',
            [target.pk],
        )

    client.force_login(actor)
    response = client.post(reverse("authentication:delete_user", args=[target.pk]))

    with connection.cursor() as cursor:
        cursor.execute('SELECT COUNT(*) FROM "relance_followup" WHERE "user_id" = %s', [target.pk])
        remaining_followups = cursor.fetchone()[0]
        cursor.execute('DROP TABLE IF EXISTS "relance_followup"')

    assert response.status_code == 302
    assert remaining_followups == 0
    assert not User.objects.filter(pk=target.pk).exists()


@pytest.mark.django_db
def test_superuser_cannot_delete_self(client):
    actor = User.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="adminpass",
    )

    client.force_login(actor)
    response = client.post(reverse("authentication:delete_user", args=[actor.pk]))

    assert response.status_code == 302
    assert User.objects.filter(pk=actor.pk).exists()


@pytest.mark.django_db
def test_non_ceo_superuser_cannot_delete_ceo_or_superuser(client):
    ceo_group, _ = Group.objects.get_or_create(name="CEO")
    ceo = User.objects.create_superuser(
        username="ceo",
        email="ceo@example.com",
        password="ceopass",
    )
    ceo.groups.add(ceo_group)
    actor = User.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="adminpass",
    )
    peer_superuser = User.objects.create_superuser(
        username="peer",
        email="peer@example.com",
        password="peerpass",
    )

    client.force_login(actor)
    ceo_response = client.post(reverse("authentication:delete_user", args=[ceo.pk]))
    peer_response = client.post(reverse("authentication:delete_user", args=[peer_superuser.pk]))

    assert ceo_response.status_code == 302
    assert peer_response.status_code == 302
    assert User.objects.filter(pk=ceo.pk).exists()
    assert User.objects.filter(pk=peer_superuser.pk).exists()


@pytest.mark.django_db
def test_ceo_can_delete_superuser(client):
    ceo_group, _ = Group.objects.get_or_create(name="CEO")
    actor = User.objects.create_superuser(
        username="ceo",
        email="ceo@example.com",
        password="ceopass",
    )
    actor.groups.add(ceo_group)
    target = User.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="adminpass",
    )

    client.force_login(actor)
    response = client.post(reverse("authentication:delete_user", args=[target.pk]))

    assert response.status_code == 302
    assert not User.objects.filter(pk=target.pk).exists()
