"""
Configuration pytest pour les tests du module management
"""
import pytest
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.models import User, Group
from django.test import Client
from unittest.mock import patch, MagicMock




@pytest.fixture(scope='session', autouse=True)
def disable_sqlite_foreign_key_checks():
    """
    Désactive la vérification des contraintes de clés étrangères pour SQLite
    """
    from django.db.backends.sqlite3 import base


    original_check = base.DatabaseWrapper.check_constraints


    def noop_check_constraints(self, table_names=None):
        pass

    base.DatabaseWrapper.check_constraints = noop_check_constraints

    yield


    base.DatabaseWrapper.check_constraints = original_check




@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    """
    Crée les tables pour les modèles non-managés
    """
    with django_db_blocker.unblock():
        from django.db import connection

        with connection.cursor() as cursor:

            cursor.execute("PRAGMA foreign_keys = OFF;")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS "Utilisateurs" (
                    "id" TEXT PRIMARY KEY,
                    "mdp" TEXT NOT NULL,
                    "email" TEXT NOT NULL,
                    "nom" TEXT,
                    "prenom" TEXT
                )
            """)


            cursor.execute("""
                CREATE TABLE IF NOT EXISTS "Modele_Relance" (
                    "utilisateur" TEXT PRIMARY KEY,
                    "metier" TEXT NOT NULL,
                    "pole" TEXT NOT NULL,
                    "message" TEXT,
                    "objet" TEXT
                )
            """)


            cursor.execute("""
                CREATE TABLE IF NOT EXISTS "Temps_Relance" (
                    "id" TEXT PRIMARY KEY,
                    "pole" TEXT NOT NULL,
                    "relance" INTEGER NOT NULL
                )
            """)


            cursor.execute("""
                CREATE TABLE IF NOT EXISTS "Activites" (
                    "id" INTEGER PRIMARY KEY AUTOINCREMENT,
                    "dossier" TEXT NOT NULL,
                    "type" TEXT NOT NULL,
                    "pole" TEXT NOT NULL,
                    "date" TIMESTAMP NOT NULL,
                    "date_type" TEXT,
                    "commentaire" TEXT
                )
            """)


            cursor.execute("""
                CREATE TABLE IF NOT EXISTS "oauth_tokens" (
                    "user_id" INTEGER PRIMARY KEY,
                    "provider" VARCHAR(50) NOT NULL DEFAULT 'google',
                    "email" VARCHAR(254) NOT NULL,
                    "access_token" TEXT NOT NULL,
                    "refresh_token" TEXT NOT NULL,
                    "token_expiry" TIMESTAMP NOT NULL,
                    "created_at" TIMESTAMP NOT NULL,
                    "updated_at" TIMESTAMP NOT NULL
                )
            """)


            cursor.execute("""
                CREATE TABLE IF NOT EXISTS "Fournisseur" (
                    "id" TEXT PRIMARY KEY,
                    "nom" TEXT,
                    "contact" TEXT NOT NULL
                )
            """)


            cursor.execute("""
                CREATE TABLE IF NOT EXISTS "Entreprise" (
                    "id" TEXT PRIMARY KEY,
                    "nom" TEXT
                )
            """)


            cursor.execute("""
                CREATE TABLE IF NOT EXISTS "Client" (
                    "id" TEXT PRIMARY KEY
                )
            """)


            cursor.execute("""
                CREATE TABLE IF NOT EXISTS "Dossier" (
                    "reference" TEXT PRIMARY KEY,
                    "type" TEXT,
                    "frais_eng" REAL DEFAULT 0,
                    "frais_payes" REAL DEFAULT 0,
                    "frais_rest" REAL DEFAULT 0,
                    "total_estim" REAL DEFAULT 0,
                    "pdf" TEXT
                )
            """)


            cursor.execute("""
                CREATE TABLE IF NOT EXISTS "technique_projectexpense" (
                    "id" INTEGER PRIMARY KEY AUTOINCREMENT,
                    "reference" TEXT,
                    "description" TEXT,
                    "amount" REAL
                )
            """)


            cursor.execute("""
                CREATE TABLE IF NOT EXISTS "Factures" (
                    "id" TEXT PRIMARY KEY,
                    "pole" TEXT NOT NULL,
                    "dossier" TEXT NOT NULL,
                    "fournisseur" TEXT NOT NULL,
                    "client" TEXT NOT NULL,
                    "montant" REAL,
                    "statut" TEXT NOT NULL,
                    "echeance" TIMESTAMP,
                    "titre" TEXT,
                    "collaborateur_id" INTEGER
                )
            """)


            cursor.execute("""
                CREATE TABLE IF NOT EXISTS "Collaborateurs" (
                    "id" INTEGER PRIMARY KEY
                )
            """)


            cursor.execute("""
                CREATE TABLE IF NOT EXISTS "Justificatifs" (
                    "facture" TEXT PRIMARY KEY
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS "pieces_upload_local" (
                    "id" INTEGER PRIMARY KEY AUTOINCREMENT,
                    "facture_id" TEXT NOT NULL,
                    "fichier" TEXT NOT NULL,
                    "uploaded_at" TIMESTAMP NOT NULL
                )
            """)

            cursor.execute("PRAGMA foreign_keys = ON;")




@pytest.fixture
def client():
    """Client Django pour les tests de vues"""
    return Client()


@pytest.fixture
def user_factory(db):
    """Factory pour créer des utilisateurs Django"""

    def create_user(**kwargs):
        defaults = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        defaults.update(kwargs)

        password = defaults.pop('password')
        user = User.objects.create_user(**defaults)
        user.set_password(password)
        user.save()
        return user

    return create_user


@pytest.fixture
def authenticated_user(user_factory):
    """Utilisateur authentifié standard"""
    return user_factory(
        username='authuser',
        email='auth@example.com',
        password='testpass123'
    )


@pytest.fixture
def admin_user(db):
    """Utilisateur admin/superuser"""
    return User.objects.create_superuser(
        username='admin',
        email='admin@test.com',
        password='admin123'
    )




@pytest.fixture
def oauth_token(db, authenticated_user):
    """Token OAuth valide pour les tests"""
    from management.modelsadm import OAuthToken

    return OAuthToken.objects.create(
        user=authenticated_user,
        provider='google',
        email=authenticated_user.email,
        access_token='test_access_token_12345',
        refresh_token='test_refresh_token_67890',
        token_expiry=timezone.now() + timedelta(hours=1),
        created_at=timezone.now(),
        updated_at=timezone.now()
    )


@pytest.fixture
def expired_oauth_token(db, authenticated_user):
    """Token OAuth expiré pour les tests"""
    from management.modelsadm import OAuthToken

    return OAuthToken.objects.create(
        user=authenticated_user,
        provider='google',
        email=authenticated_user.email,
        access_token='expired_access_token',
        refresh_token='test_refresh_token',
        token_expiry=timezone.now() - timedelta(hours=1),
        created_at=timezone.now() - timedelta(days=1),
        updated_at=timezone.now() - timedelta(days=1)
    )




@pytest.fixture
def utilisateur(db):
    """Utilisateur de la table Utilisateurs (client/destinataire)"""
    from management.modelsadm import Utilisateur

    return Utilisateur.objects.create(
        id='USER-001',
        mdp='hashed_password',
        email='client@example.com',
        nom='Dupont',
        prenom='Jean'
    )


@pytest.fixture
def modele_relance(db, utilisateur):
    """Modèle de relance pour un utilisateur"""
    from management.modelsadm import Modele_Relance

    return Modele_Relance.objects.create(
        utilisateur=utilisateur.id,
        metier='Immobilier',
        pole='Administratif',
        message='Bonjour, ceci est une relance automatique concernant votre dossier.',
        objet='Relance Dossier'
    )


@pytest.fixture
def temps_relance(db, utilisateur):
    """Configuration de délai de relance"""
    from management.modelsadm import Temps_Relance

    return Temps_Relance.objects.create(
        id=utilisateur.id,
        pole='Administratif',
        relance=7
    )


@pytest.fixture
def activite_future(db):
    """Activité prévue dans le futur"""
    from management.modelsadm import Activites

    future_date = timezone.now() + timedelta(days=7)

    return Activites.objects.create(
        dossier='DOSS-2024-001',
        type='visite',
        pole='Administratif',
        date=future_date,
        date_type='Date',
        commentaire='Visite de contrôle'
    )


@pytest.fixture
def activite_proche(db):
    """Activité prévue dans 1 jour"""
    from management.modelsadm import Activites

    tomorrow = timezone.now() + timedelta(days=1)

    return Activites.objects.create(
        dossier='DOSS-2024-002',
        type='compromis',
        pole='Administratif',
        date=tomorrow,
        date_type='Date',
        commentaire='Signature compromis urgent'
    )




@pytest.fixture
def mock_gmail_service():
    """Mock du service Gmail API"""
    mock_service = MagicMock()


    mock_list_response = {
        'messages': [
            {'id': 'msg_001', 'threadId': 'thread_001'},
            {'id': 'msg_002', 'threadId': 'thread_002'},
        ]
    }
    mock_service.users().messages().list().execute.return_value = mock_list_response

    mock_get_response = {
        'id': 'msg_001',
        'threadId': 'thread_001',
        'payload': {
            'headers': [
                {'name': 'Subject', 'value': 'Test Email'},
                {'name': 'To', 'value': 'client@example.com'},
                {'name': 'Date', 'value': 'Mon, 1 Jan 2024 10:00:00 +0000'},
                {'name': 'Message-ID', 'value': '<test@gmail.com>'}
            ],
            'body': {'data': 'VGVzdCBib2R5'}
        }
    }
    mock_service.users().messages().get().execute.return_value = mock_get_response


    mock_send_response = {'id': 'sent_msg_001'}
    mock_service.users().messages().send().execute.return_value = mock_send_response

    return mock_service


@pytest.fixture
def mock_gmail_credentials():
    """Mock des credentials Google"""
    mock_creds = MagicMock()
    mock_creds.token = 'mock_access_token'
    mock_creds.refresh_token = 'mock_refresh_token'
    mock_creds.expiry = timezone.now() + timedelta(hours=1)
    return mock_creds


@pytest.fixture
def patch_gmail_service(mock_gmail_service):
    """Patch automatique du service Gmail pour tous les tests"""
    with patch('management.oauth_utils.build', return_value=mock_gmail_service):
        yield mock_gmail_service




@pytest.fixture
def complete_relance_setup(
        db,
        authenticated_user,
        oauth_token,
        utilisateur,
        modele_relance,
        temps_relance
):
    """
    Configuration complète pour tester les relances automatiques
    Retourne un dictionnaire avec tous les objets nécessaires
    """
    return {
        'user': authenticated_user,
        'oauth_token': oauth_token,
        'utilisateur': utilisateur,
        'modele_relance': modele_relance,
        'temps_relance': temps_relance
    }


@pytest.fixture
def sent_email_data():
    """Données d'email envoyé pour les tests"""
    return {
        'id': 'msg_test_001',
        'thread_id': 'thread_test_001',
        'subject': 'Test Email Subject',
        'to': 'client@example.com',
        'date': timezone.now() - timedelta(days=7),
        'status': 'pending'
    }




@pytest.fixture
def pole_administratif_group(db):
    """Groupe Pôle Administratif"""
    return Group.objects.get_or_create(name='POLE_ADMINISTRATIF')[0]


@pytest.fixture
def admin_user_with_access(db, user_factory, pole_administratif_group):
    """Utilisateur avec accès au pôle administratif"""
    user = user_factory(username='admin_pole')
    user.groups.add(pole_administratif_group)
    return user




@pytest.fixture
def freeze_time():
    """Fixture pour figer le temps dans les tests"""

    def _freeze(frozen_time):
        with patch('django.utils.timezone.now', return_value=frozen_time):
            yield frozen_time

    return _freeze


@pytest.fixture
def capture_emails():
    """Capture les emails envoyés pendant le test"""
    from django.core import mail
    mail.outbox = []
    return mail.outbox



@pytest.fixture
def pdf_simple():
    """Génère un PDF simple d'une page pour les tests"""
    from io import BytesIO
    from reportlab.pdfgen import canvas as pdf_canvas

    buffer = BytesIO()
    c = pdf_canvas.Canvas(buffer, pagesize=(595, 842))
    c.drawString(100, 750, "Document de test - Page 1")
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


@pytest.fixture
def pdf_multi_pages():
    """Génère un PDF de plusieurs pages pour les tests"""
    from io import BytesIO
    from reportlab.pdfgen import canvas as pdf_canvas

    buffer = BytesIO()
    c = pdf_canvas.Canvas(buffer, pagesize=(595, 842))


    c.drawString(100, 750, "Document de test - Page 1")
    c.showPage()


    c.drawString(100, 750, "Document de test - Page 2")
    c.showPage()


    c.drawString(100, 750, "Document de test - Page 3")
    c.showPage()

    c.save()
    buffer.seek(0)
    return buffer


@pytest.fixture
def image_signature():
    """Image de signature factice"""
    from django.core.files.uploadedfile import SimpleUploadedFile

    png_data = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01'
        b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    return SimpleUploadedFile("signature.png", png_data, content_type="image/png")


@pytest.fixture
def image_tampon():
    """Image de tampon factice"""
    from django.core.files.uploadedfile import SimpleUploadedFile

    png_data = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01'
        b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    return SimpleUploadedFile("tampon.png", png_data, content_type="image/png")


@pytest.fixture
def document_pdf_simple(db, pdf_simple):
    """Document de test avec PDF simple d'une page"""
    from signatures.models import Document
    from django.core.files.base import ContentFile

    doc = Document.objects.create(titre="Document Test Simple")
    doc.fichier.save('test_simple.pdf', ContentFile(pdf_simple.read()), save=True)

    return doc


@pytest.fixture
def document_pdf_multi(db, pdf_multi_pages):
    """Document de test avec PDF multi-pages"""
    from signatures.models import Document
    from django.core.files.base import ContentFile

    doc = Document.objects.create(titre="Document Test Multi-pages")
    doc.fichier.save('test_multi.pdf', ContentFile(pdf_multi_pages.read()), save=True)

    return doc


@pytest.fixture
def signature_user_ceo(db, user_factory, image_signature):
    """SignatureUser (CEO) avec image de signature"""
    from signatures.models import SignatureUser

    user = user_factory(username='ceo', email='ceo@benjamin-immo.fr')

    sig_user = SignatureUser.objects.create(user=user)
    sig_user.image.save('ceo_signature.png', image_signature, save=True)

    return sig_user


@pytest.fixture
def tampon_entreprise(db, image_tampon):
    """Tampon officiel de l'entreprise"""
    from signatures.models import Tampon

    tampon = Tampon.objects.create(nom="Tampon Benjamin Immobilier")
    tampon.image.save('tampon_officiel.png', image_tampon, save=True)

    return tampon


@pytest.fixture
def document_workflow(db, pdf_simple):
    """Document de test pour le workflow"""
    from signatures.models import Document
    from django.core.files.base import ContentFile

    doc = Document.objects.create(titre="Document Workflow Test")
    doc.fichier.save('workflow_test.pdf', ContentFile(pdf_simple.read()), save=True)

    return doc