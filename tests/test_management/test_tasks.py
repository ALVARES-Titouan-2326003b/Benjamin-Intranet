"""
Tests pour le module tasks
Tests des tâches Celery pour les relances automatiques et rappels d'activités
"""
import pytest
from datetime import timedelta
from django.utils import timezone
from unittest.mock import patch

from management.tasks import (
    check_and_send_auto_relances,
    check_and_send_activite_reminders,
    get_sent_emails_for_celery,
)
from management.modelsadm import Activites





@pytest.mark.django_db
class TestCheckAndSendAutoRelances:
    """Tests pour la tâche de relances automatiques"""

    def test_no_oauth_users(self, db):
        """
        Teste check_and_send_auto_relances sans utilisateurs OAuth
        Devrait retourner success=True avec 0 emails traités
        """
        result = check_and_send_auto_relances()

        assert result['success'] is True
        assert result['emails_traites'] == 0
        assert result['relances_envoyees'] == 0
        assert result['erreurs'] == 0

    def test_with_oauth_but_no_emails(
            self,
            authenticated_user,
            oauth_token,
            mock_gmail_service
    ):
        """
        Teste avec un utilisateur OAuth mais sans emails envoyés
        Devrait s'exécuter sans erreur
        """
        with patch(
                'management.tasks.get_sent_emails_for_celery',
                return_value=[]
        ):
            result = check_and_send_auto_relances()

            assert result['success'] is True
            assert result['emails_traites'] == 0
            assert result['relances_envoyees'] == 0

    def test_with_replied_email(
            self,
            complete_relance_setup,
            mock_gmail_service
    ):
        """
        Teste avec un email qui a déjà reçu une réponse
        Ne devrait PAS envoyer de relance
        """
        replied_email = {
            'id': 'msg_001',
            'subject': 'Test',
            'to': complete_relance_setup['utilisateur'].email,
            'date': timezone.now() - timedelta(days=7),
            'status': 'replied'
        }

        with patch(
                'management.tasks.get_sent_emails_for_celery',
                return_value=[replied_email]
        ):
            result = check_and_send_auto_relances()

            assert result['success'] is True
            assert result['relances_envoyees'] == 0
            assert result['debug']['status_replied'] == 1

    def test_with_pending_email_wrong_interval(
            self,
            complete_relance_setup,
            mock_gmail_service
    ):
        """
        Teste avec un email en attente mais pas au bon intervalle
        Ne devrait PAS envoyer de relance (modulo check)
        """

        pending_email = {
            'id': 'msg_001',
            'subject': 'Test',
            'to': complete_relance_setup['utilisateur'].email,
            'date': timezone.now() - timedelta(days=5),
            'status': 'pending'
        }

        with patch(
                'management.tasks.get_sent_emails_for_celery',
                return_value=[pending_email]
        ):
            result = check_and_send_auto_relances()

            assert result['success'] is True
            assert result['relances_envoyees'] == 0
            assert result['debug']['modulo_check'] == 1



    def test_send_relance_failure(
            self,
            complete_relance_setup,
            mock_gmail_service
    ):
        """
        Teste l'échec d'envoi d'une relance
        L'erreur devrait être comptée mais ne pas crasher
        """
        pending_email = {
            'id': 'msg_001',
            'subject': 'Test',
            'to': complete_relance_setup['utilisateur'].email,
            'date': timezone.now() - timedelta(days=7),
            'status': 'pending'
        }

        with patch(
                'management.tasks.get_sent_emails_for_celery',
                return_value=[pending_email]
        ):
            with patch('management.email_manager.send_auto_relance') as mock_send:
                mock_send.return_value = {'success': False, 'message': 'API Error'}

                result = check_and_send_auto_relances()

                assert result['success'] is True
                assert result['relances_envoyees'] == 0
                assert result['erreurs'] == 1
                assert result['debug']['send_failed'] == 1

    def test_missing_utilisateur(
            self,
            authenticated_user,
            oauth_token,
            mock_gmail_service
    ):
        """
        Teste avec un email vers un destinataire non présent dans Utilisateurs
        Ne devrait PAS envoyer de relance
        """
        pending_email = {
            'id': 'msg_001',
            'subject': 'Test',
            'to': 'unknown@example.com',
            'date': timezone.now() - timedelta(days=7),
            'status': 'pending'
        }

        with patch(
                'management.tasks.get_sent_emails_for_celery',
                return_value=[pending_email]
        ):
            result = check_and_send_auto_relances()

            assert result['success'] is True
            assert result['relances_envoyees'] == 0
            assert result['debug']['utilisateur_not_found'] == 1

    def test_missing_modele_relance(
            self,
            authenticated_user,
            oauth_token,
            utilisateur,
            temps_relance
    ):
        """
        Teste avec un utilisateur sans modèle de relance
        Ne devrait PAS envoyer de relance
        """
        pending_email = {
            'id': 'msg_001',
            'subject': 'Test',
            'to': utilisateur.email,
            'date': timezone.now() - timedelta(days=7),
            'status': 'pending'
        }

        with patch(
                'management.tasks.get_sent_emails_for_celery',
                return_value=[pending_email]
        ):
            result = check_and_send_auto_relances()

            assert result['success'] is True
            assert result['relances_envoyees'] == 0
            assert result['debug']['modele_relance_not_found'] == 1



@pytest.mark.django_db
class TestGetSentEmailsForCelery:
    """Tests pour la récupération d'emails dans les tâches Celery"""

    def test_get_emails_without_oauth(self, authenticated_user):
        """
        Teste get_sent_emails_for_celery sans token OAuth
        Devrait retourner une liste vide
        """
        result = get_sent_emails_for_celery(authenticated_user, limit=10)

        assert result == []
        assert isinstance(result, list)

    def test_get_emails_with_oauth(
            self,
            authenticated_user,
            oauth_token,
            mock_gmail_service
    ):
        """
        Teste get_sent_emails_for_celery avec un token OAuth valide
        Devrait retourner une liste d'emails
        """
        with patch('management.oauth_utils.build', return_value=mock_gmail_service):
            with patch('management.oauth_utils.get_valid_credentials'):
                with patch('management.email_manager.check_if_replies_exist', return_value=set()):
                    result = get_sent_emails_for_celery(authenticated_user, limit=10)

                    assert isinstance(result, list)
                    assert len(result) > 0

                    first_email = result[0]
                    assert 'id' in first_email
                    assert 'thread_id' in first_email
                    assert 'subject' in first_email
                    assert 'to' in first_email
                    assert 'date' in first_email
                    assert 'status' in first_email


@pytest.mark.django_db
class TestCheckAndSendActiviteReminders:
    """Tests pour les rappels d'activités"""

    def test_no_activities(self, db):
        """
        Teste check_and_send_activite_reminders sans activités
        Devrait retourner success=True avec 0 activités traitées
        """
        result = check_and_send_activite_reminders()

        assert result['success'] is True
        assert result['activites_traitees'] == 0
        assert result['rappels_envoyes'] == 0

    def test_with_past_activity(self, db):
        """
        Teste avec une activité passée
        Ne devrait PAS envoyer de rappel
        """
        past_date = timezone.now() - timedelta(days=1)

        Activites.objects.create(
            dossier='PAST-001',
            type='visite',
            pole='Administratif',
            date=past_date,
            date_type='Date'
        )

        result = check_and_send_activite_reminders()

        assert result['success'] is True
        assert result['activites_traitees'] == 0

    def test_with_far_future_activity(self, db):
        """
        Teste avec une activité trop éloignée (>10 jours)
        Ne devrait PAS envoyer de rappel
        """
        far_future = timezone.now() + timedelta(days=15)

        Activites.objects.create(
            dossier='FAR-001',
            type='visite',
            pole='Administratif',
            date=far_future,
            date_type='Date'
        )

        result = check_and_send_activite_reminders()

        assert result['success'] is True
        assert result['activites_traitees'] == 0

    @pytest.mark.parametrize('days_ahead', [1, 4, 7, 10])
    def test_send_reminder_at_correct_intervals(self, db, days_ahead, capture_emails):
        """
        Teste l'envoi de rappels aux intervalles corrects (J-1, J-4, J-7, J-10)
        """
        activity_date = timezone.now() + timedelta(days=days_ahead)

        Activites.objects.create(
            dossier=f'DOSS-{days_ahead}J',
            type='visite',
            pole='Administratif',
            date=activity_date,
            date_type='Date',
            commentaire='Activité de test'
        )

        result = check_and_send_activite_reminders()

        assert result['success'] is True
        assert result['activites_traitees'] == 1
        assert result['rappels_envoyes'] == 1


        assert len(capture_emails) == 1

        email = capture_emails[0]
        assert f'J-{days_ahead}' in email.subject
        assert f'DOSS-{days_ahead}J' in email.body

    def test_no_reminder_for_wrong_interval(self, db, capture_emails):
        """
        Teste qu'aucun rappel n'est envoyé pour les intervalles incorrects
        (ex: J-3, J-5, J-6, J-8, J-9)
        """

        activity_date = timezone.now() + timedelta(days=3)

        Activites.objects.create(
            dossier='DOSS-3J',
            type='visite',
            pole='Administratif',
            date=activity_date,
            date_type='Date'
        )

        result = check_and_send_activite_reminders()

        assert result['success'] is True
        assert result['activites_traitees'] == 1
        assert result['rappels_envoyes'] == 0
        assert len(capture_emails) == 0

    def test_multiple_activities_same_day(self, db, capture_emails):
        """
        Teste avec plusieurs activités le même jour
        Devrait envoyer un rappel pour chaque activité
        """
        tomorrow = timezone.now() + timedelta(days=1)

        Activites.objects.create(
            dossier='DOSS-A',
            type='visite',
            pole='Administratif',
            date=tomorrow,
            date_type='Date'
        )

        Activites.objects.create(
            dossier='DOSS-B',
            type='compromis',
            pole='Administratif',
            date=tomorrow,
            date_type='Date'
        )

        result = check_and_send_activite_reminders()

        assert result['success'] is True
        assert result['activites_traitees'] == 2
        assert result['rappels_envoyes'] == 2
        assert len(capture_emails) == 2

    def test_reminder_email_content(self, db, capture_emails):
        """
        Teste le contenu de l'email de rappel
        Devrait contenir toutes les infos de l'activité
        """
        tomorrow = timezone.now() + timedelta(days=1)

        Activites.objects.create(
            dossier='DOSS-URGENT',
            type='compromis',
            pole='Administratif',
            date=tomorrow,
            date_type='Date',
            commentaire='Signature importante - ne pas oublier'
        )

        result = check_and_send_activite_reminders()

        assert len(capture_emails) == 1

        email = capture_emails[0]

        assert 'DOSS-URGENT' in email.body
        assert 'compromis' in email.body
        assert 'Signature importante' in email.body
        assert 'J-1' in email.subject

    def test_exception_handling(self, db):
        """
        Teste que les exceptions ne font pas crasher toute la tâche
        """
        tomorrow = timezone.now() + timedelta(days=1)

        Activites.objects.create(
            dossier='GOOD-ACTIVITY',
            type='visite',
            pole='Administratif',
            date=tomorrow,
            date_type='Date'
        )

        with patch('django.core.mail.EmailMessage.send') as mock_send:

            mock_send.side_effect = [Exception("SMTP Error"), None]


            Activites.objects.create(
                dossier='SECOND-ACTIVITY',
                type='visite',
                pole='Administratif',
                date=tomorrow,
                date_type='Date'
            )

            result = check_and_send_activite_reminders()
            assert result['success'] is True
            assert result['activites_traitees'] == 2
            assert result['rappels_envoyes'] == 1